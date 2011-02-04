function makeImdbForm(mid, imdb)
{
    return(
        '<div class="imdb_form suggestion_form" id="imdbform_' + mid + '">' +
            'Confirm or suggest address of another IMDb page:<br/>' +
            '<input name="imdb" type="text" value="' + imdb + '"/> <input type="submit" value="Ok"/>' +
        '</div>');
}

function setupImdbFormCallbacks(the_form, mid, closeCB, guessed)
{
    imdb_input = the_form.find('input[type=text]');
    the_form.find('input[type=submit]').click(function() {
        imdb = imdb_input.val();
        $.post("/imdb_suggest", { mid: mid, imdb: imdb }, function() {
            refetchData(mid);
        });
        the_form.html("Thank you!");
        setTimeout(function() { closeCB(); guessed.remove(); }, 666);
    });
}

function setupImdbHandler(param) {
    var title = $(this).attr("title");
    $(this).attr("title", title + " Please click here to suggest another one or confirm.");
    var td = $(this).parents("td");
    var midref = td.find(".mid").attr("href");
    this.mid = midref.replace(/.*mid=(.*)/, '$1');
    var imdbtd = td.next(".imdb");
    this.imdb = imdbtd.find("a").attr("href");

    $(this).click(function() {
        guessed = this;
        closeCB = function() { $(guessed.imdb_form).fadeOut("slow", function() { $(this).remove(); guessed.imdb_form = null; }); };
        if (this.imdb_form) {
            closeCB();
        } else {
            td = $(this).parents("td");
            td.append(makeImdbForm(this.mid, this.imdb));
            imdb_form = td.find(".imdb_form");
            setupImdbFormCallbacks(imdb_form, this.mid, closeCB, $(this));
            imdb_form.hide().fadeIn("slow");
            this.imdb_form = imdb_form;
        }
        return false;
    });
}

$(".imdb_status").each(setupImdbHandler);
