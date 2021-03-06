from bottle import request, response, HTTPError

from webrecorder.basecontroller import BaseController


# ============================================================================
class RecsController(BaseController):
    def init_routes(self):
        @self.app.post('/api/v1/recordings')
        def create_recording():
            user, coll = self.get_user_coll(api=True)

            title = request.forms.get('title')

            coll_title = request.forms.get('coll_title')

            rec = self.sanitize_title(title)

            recording = self.manager.create_recording(user, coll, rec, title, coll_title)

            return {'recording': recording}

        @self.app.get('/api/v1/recordings')
        def get_recordings():
            user, coll = self.get_user_coll(api=True)

            rec_list = self.manager.get_recordings(user, coll)

            return {'recordings': rec_list}

        @self.app.get('/api/v1/recordings/<rec>')
        def get_recording(rec):
            user, coll = self.get_user_coll(api=True)

            return self.get_rec_info(user, coll, rec)

        @self.app.delete('/api/v1/recordings/<rec>')
        def delete_recording(rec):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            self.manager.delete_recording(user, coll, rec)

            return {'deleted_id': rec}

        @self.app.post('/api/v1/recordings/<rec>/rename/<new_rec_title>')
        def rename_recording(rec, new_rec_title):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            new_rec = self.sanitize_title(new_rec_title)

            if not new_rec:
                err_msg = 'invalid recording title ' + new_rec_title
                return {'error_message': err_msg}

            if rec == new_rec:
                return {'rec_id': rec, 'coll_id': coll, 'title': new_rec_title}

            #if self.manager.has_recording(user, coll, new_rec):
            #    err_msg = 'rec "{0}" already exists'.format(new_rec)
            #    return {'error_message': err_msg}

            res = self.manager.rename(user=user,
                                      coll=coll,
                                      new_coll=coll,
                                      rec=rec,
                                      new_rec=new_rec,
                                      title=new_rec_title)

            return res


        @self.app.post('/api/v1/recordings/<rec>/move/<new_coll>')
        def move_recording(rec, new_coll):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            if not self.manager.has_collection(user, new_coll):
                err_msg = 'collection "{0}" does not exist'.format(new_coll)
                return {'error_message': err_msg}

            res = self.manager.rename(user=user,
                                      coll=coll,
                                      new_coll=new_coll,
                                      rec=rec,
                                      new_rec=rec,
                                      title=new_rec_title)

            return res

        @self.app.post('/api/v1/recordings/<rec>/pages')
        def add_page(rec):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            page_data = dict(request.forms.decode())

            res = self.manager.add_page(user, coll, rec, page_data)
            return res

        @self.app.post('/api/v1/recordings/<rec>/page')
        def modify_page(rec):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            page_data = dict(request.forms.decode())

            res = self.manager.modify_page(user, coll, rec, page_data)
            return {'page-data': page_data, 'recording-id': rec}

        @self.app.get('/api/v1/recordings/<rec>/pages')
        def list_pages(rec):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            pages = self.manager.list_pages(user, coll, rec)
            return {'pages': pages}

        @self.app.get('/api/v1/recordings/<rec>/num_pages')
        def get_num_pages(rec):
            user, coll = self.get_user_coll(api=True)

            return {'count': self.manager.count_pages(user, coll, rec) }

        @self.app.delete('/api/v1/recordings/<rec>/pages')
        def delete_page(rec):
            user, coll = self.get_user_coll(api=True)
            self._ensure_rec_exists(user, coll, rec)

            url = request.forms.get('url')
            ts = request.forms.get('timestamp')

            return self.manager.delete_page(user, coll, rec, url, ts)

        # LOGGED-IN NEW REC
        @self.app.get(['/<user>/<coll>/$new', '/<user>/<coll>/$new/'])
        @self.jinja2_view('new_recording.html')
        def new_recording(user, coll):

            return self.get_rec_info_for_new(user, coll, None, 'new_recording')

        # LOGGED-IN ADD TO REC
        @self.app.get(['/<user>/<coll>/<rec>/$add', '/<user>/<coll>/<rec>/$add/'])
        @self.jinja2_view('add_to_recording.html')
        def add_to_recording(user, coll, rec):

            return self.get_rec_info_for_new(user, coll, rec, 'add_to_recording')

        # LOGGED-IN REC VIEW
        #@self.app.get(['/<user>/<coll>/<rec>', '/<user>/<coll>/<rec>/'])
        #@self.jinja2_view('recording_info.html')
        #def rec_info(user, coll, rec):

        #    return self.get_rec_info_for_view(user, coll, rec)

        # DELETE REC
        @self.app.post('/_delete_rec/<rec>')
        def delete_rec_post(rec):
            user, coll = self.get_user_coll(api=False)

            success = False
            try:
                success = self.manager.delete_recording(user, coll, rec)
            except Exception as e:
                print(e)

            if success:
                self.flash_message('Recording {0} has been deleted!'.format(rec), 'success')
                self.redirect(self.get_path(user, coll))
            else:
                self.flash_message('There was an error deleting {0}'.format(rec))
                self.redirect(self.get_path(user, coll, rec))

    def get_rec_info(self, user, coll, rec):
        recording = self.manager.get_recording(user, coll, rec)

        if not recording:
            response.status = 404
            return {'error_message': 'Recording not found', 'id': rec}

        return {'recording': recording}

    def get_rec_info_for_view(self, user, coll, rec):
        result = self.get_rec_info(user, coll, rec)
        if result.get('error_message'):
            self._raise_error(404, 'Recording not found')

        result['size_remaining'] = self.manager.get_size_remaining(user)
        result['collection'] = self.manager.get_collection(user, coll)
        result['pages'] = self.manager.list_pages(user, coll, rec)

        result['user'] = self.get_view_user(user)
        result['coll'] = coll
        result['rec'] = rec

        result['rec_title'] = result['recording']['title']
        result['coll_title'] = result['collection']['title']

        return result

    def get_rec_info_for_new(self, user, coll, rec, action):
        result = {'curr_mode': 'new', 'action': action}
        result['user'] = self.get_view_user(user)
        result['coll'] = coll
        result['rec'] = rec

        collection = self.manager.get_collection(user, coll)
        if not collection:
            self._raise_error(404, 'Collection not found')

        result['coll_title'] = collection['title']

        if rec:
            recording = self.manager.get_recording(user, coll, rec)
            if not recording:
                self._raise_error(404, 'Recording not found')

            result['rec_title'] = recording['title']

        return result

    def _ensure_rec_exists(self, user, coll, rec):
        if not self.manager.has_recording(user, coll, rec):
            self._raise_error(404, 'Recording not found', api=True,
                              id=rec)

