var fetchQueue = [];

function enqueueFetch(mid) {
    fetchQueue.push(mid);
}

function processFetchQueue() {
    var mid = fetchQueue.shift();
    if (mid) {
        $.get("/data?mid=" + mid, function(data) {
            var tr = $("#movie_" + mid);
            var showtimes = tr.find(".showtimes").html();
            tr.replaceWith(data);
            $("#movie_" + mid).find(".showtimes").html(showtimes);
            processFetchQueue();
        });
    }
}
