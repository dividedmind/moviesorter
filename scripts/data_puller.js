var fetchQueue = [];

function enqueueFetch(mid) {
    fetchQueue.push(mid);
}

function processFetchQueue() {
    var mid = fetchQueue.shift();
    if (mid) {
        $.get("/data?mid=" + mid, function(data) {
            $("#movie_" + mid).replaceWith(data);
            processFetchQueue();
        });
    }
}
