$(function() {
    var DEFAULT_RECORDING_SESSION_NAME = "Recording Session";

    // 'New recording': Start button
    $('header').on('submit', '.start-recording', startNewRecording);

    // 'Homepage': 'Record' button
    $('.wr-content').on('submit', '.start-recording-homepage', startNewRecording);


    function startNewRecording(event) {
        event.preventDefault();

        var collection;

        if (!user) {
            user = "$temp";
            collection = "temp";
        } else {
            collection = $('[data-collection-id]').attr('data-collection-id');
        }

        var title = $("input[name='rec-title']").val();
        var url = $("input[name='url']").val();

        var success = function(data) {
            title = data.recording.title;
            var id = data.recording.id;

            RouteTo.recordingInProgress(user, collection, id, url);
        };

        var fail = function(data) {
            //NOP
        }

        var attrs = {"title": title,
                     "coll_title": "Temporary Collection"}

        setStorage("__wr_currRec", title);

        Recordings.create(user, collection, attrs, success, fail);
    };

    function setStorage(name, value) {
        if (window.sessionStorage) {
            window.sessionStorage.setItem(name, value);
        }

        if (window.localStorage) {
            window.localStorage.setItem(name, value);
        }
    }

    function getStorage(name) {
        var value = undefined;

        // First try session, then local
        if (window.sessionStorage) {
            value = window.sessionStorage.getItem(name);
        }

        if (!value && window.localStorage) {
            value = window.localStorage.getItem(name);
        }

        return value;
    }


    // 'Homepage': Logged in collection dropdown select
    $('.wr-content').on('click', '.collection-select', function(event) {
        event.preventDefault();

        var currColl = $(this).data('collection-id');

        $('.dropdown-toggle-collection').html(
            $('<span class="dropdown-toggle-label" data-collection-id="' +
                currColl + '">' +
                    $(this).text() + " " +
                '<span class="caret"></span>'));

        setStorage("__wr_currColl", currColl);
    });

    $("#create-coll").on('submit', function(event) {
        var collection = $(this).find("#collection-id").val();
        setStorage("__wr_currColl", currColl);
    });

    // Set default recording title
    var currRec = getStorage("__wr_currRec");

    if (!currRec) {
        currRec = DEFAULT_RECORDING_SESSION_NAME;
    }

    $("input[name='rec-title']").val(currRec);

    // Only for logged in users below
    if (!user) {
        return;
    }

    // If logged-in user and has collection selector (homepage)
    // select first collection
    var currColl = getStorage("__wr_currColl");

    var collSelect = undefined;

    if (currColl) {
        collSelect = $(".dropdown a[data-collection-id='" + currColl + "']");
    }

    if (!collSelect || !collSelect.length) {
        collSelect = $(".collection-select");
    }

    if (collSelect && collSelect.length > 0) {
        collSelect[0].click();
    }
});



