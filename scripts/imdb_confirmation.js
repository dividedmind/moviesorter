function makeImdbForm(mid, imdb)
{
    return(
        '<div class="imdb_form" id="imdbform_' + mid + '">' +
            'Confirm or suggest address of another IMDb page:<br/>' +
            '<input name="imdb" type="text" value="' + imdb + '"/> <input type="submit" value="Ok"/>' +
        '</div>');
}

guessed = $(".imdb_guessed");
title = guessed.attr("title");
guessed.attr("title", title + " Please click here to confirm it or suggest another one.");

guessed.each(function(i) {
    td = $(this).parents("td");
    midref = td.find(".mid").attr("href");
    this.mid = midref.replace(/.*mid=(.*)/, '$1');
    imdbtd = td.next(".imdb");
    this.imdb = imdbtd.find("a").attr("href");

    $(this).click(function() {
        guessed = this;
        if (this.imdb_form) {
            $(this.imdb_form).fadeOut("slow", function() { $(this).remove(); guessed.imdb_form = null; });
        } else {
            td = $(this).parents("td");
            td.append(makeImdbForm(this.mid, this.imdb));
            td.find(".imdb_form").hide().fadeIn("slow");
            this.imdb_form = td.find(".imdb_form");
        }
        return false;
    });
});
