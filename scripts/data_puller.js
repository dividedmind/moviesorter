var fetchQueue = [];

function enqueueFetch(mid) {
    fetchQueue.push(mid);
}

function refetchData(mid) {
    $.get("/data?" + $.param({mid: mid, city: city}), function(data) {
        var tr = $("#movie_" + mid);
        var showtimes = tr.find(".showtimes").html();
        tr.replaceWith(data);
        tr = $("#movie_" + mid);
        tr.find(".showtimes").html(showtimes);
        setupImdbHandler.apply(tr.find(".imdb_status")[0]);
        setupCritickerHandler.apply(tr.find(".criticker_notfound")[0]);
        processFetchQueue();
    });
}

function processFetchQueue() {
    var mid = fetchQueue.shift();
    if (mid) {
        refetchData(mid);
    }
}
