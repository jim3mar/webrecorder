import os
import glob
import redis
import datetime
import fcntl


# ============================================================================
class StorageCommitter(object):
    def __init__(self, config):
        self.redis_base_url = os.environ['REDIS_BASE_URL']

        self.redis = redis.StrictRedis.from_url(self.redis_base_url)

        self.record_root_dir = os.environ['RECORD_ROOT']

        self.glob_pattern = self.record_root_dir + '*/*/*/*.warc.gz'

        self.warc_key_templ = config['warc_key_templ']
        self.warc_upload_wait_templ = config['warc_upload_wait_templ']

        self.default_storage_profile = self.create_default_profile(config)

        self.storage_class_map = {}

        self.storage_key_templ = config['storage_key_templ']
        self.info_key_templ = config['info_key_templ']

        self.upload_wait_secs = int(config['upload_wait_secs'])

        print('Storage Committer Root: ' + self.record_root_dir)

    def create_default_profile(self, config):
        storage_type = os.environ.get('DEFAULT_STORAGE', 'local')

        profile = {'type': storage_type}

        if storage_type == 's3':
            s3_root = os.environ.get('S3_ROOT')
            s3_root += config['storage_path_templ']

            profile['remote_url_templ'] = s3_root

        return profile

    def is_locked(self, filename):
        with open(filename, 'rb') as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return False
            except Exception as e:
                print(e)
                print('Skipping {0}, not yet done'.format(filename))
                return True

    def is_temp(self, user):
        return user.startswith('temp!')

    def __call__(self):
        if not os.path.isdir(self.record_root_dir):
            return

        print('Checking for new warcs in {0}'.format(self.record_root_dir))

        for full_filename in glob.glob(self.glob_pattern):
            if self.is_locked(full_filename):
                continue

            relpath = os.path.relpath(full_filename, self.record_root_dir)

            parts = relpath.split('/')

            if len(parts) != 4:
                print('Invalid file match: ' + relpath)
                continue

            user, coll, rec, warcname = parts

            if self.is_temp(user):
                continue

            storage = self.get_storage(user, coll, rec)
            if not storage:
                continue

            warc_upload_wait = self.warc_upload_wait_templ.format(filename=full_filename)

            if self.redis.get(warc_upload_wait) != b'1':
                if not storage.upload_file(user, coll, rec, warcname, full_filename):
                    continue

                self.redis.setex(warc_upload_wait, self.upload_wait_secs, 1)

            # already uploaded, see if it is accessible
            # if so, finalize and delete original
            remote_url = storage.get_valid_remote_url(user, coll, rec, warcname)
            if remote_url:
                self.commit_uploaded(user, coll, rec, warcname, full_filename, remote_url)
            else:
                print('Not yet available: {0}'.format(full_filename))

    def commit_uploaded(self, user, coll, rec, warcname, full_filename, remote_url):
        # update path index to point to remote url!
        key = self.warc_key_templ.format(user=user, coll=coll, rec=rec)
        self.redis.hset(key, warcname, remote_url)

        print('Commit Verified, Deleting: {0}'.format(full_filename))
        os.remove(full_filename)

    def get_storage(self, user, coll, rec):
        if self.is_temp(user):
            return None

        info_key = self.info_key_templ['coll'].format(user=user, coll=coll)

        storage_type = self.redis.hget(info_key, 'storage_type')

        config = None

        # attempt to find storage profile by name
        if storage_type:
            config = self.redis.hgetall(self.storage_key_templ.format(name=storage_type))

        # default storage profile
        if not config:
            config = self.default_storage_profile

        # storage profile class stored in profile 'type'
        storage_class = self.storage_class_map.get(config['type'])

        # keeping local storage only
        if not storage_class:
            return None

        return storage_class(config)

    def add_storage_class(self, type_, cls):
        self.storage_class_map[type_] = cls

