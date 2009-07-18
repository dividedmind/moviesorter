function makeCritickerSuggestionForm(imdb)
{
    return(
        '<div class="criticker suggestion_form" id="critform_' + imdb + '">' +
            'Enter address of Criticker page:<br/>' +
            '<input name="criticker" type="text" value=""/> <input type="submit" value="Ok"/>' +
        '</div>');
}

function setupCritFormCallbacks(the_form, imdb, closeCB, guessed)
{
    crit_input = the_form.find('input[type=text]');
    the_form.find('input[type=submit]').click(function() {
        crit = crit_input.val();
        $.post("/criticker_suggest", { imdb: imdb, criticker: crit });
        the_form.html("Thank you!");
        setTimeout(function() { closeCB(); guessed.remove(); }, 666);
    });
}

$(".criticker_notfound").each(function(i) {
    title = $(this).attr("title");
    $(this).attr("title", title + " If you think it's there, click here to suggest an address.");
    tr = $(this).parents("tr");
    imdbtd = tr.find(".imdb");
    this.imdb = imdbtd.find("a").attr("href");

    $(this).click(function() {
        notfound = this;
        closeCB = function() { $(notfound.crit_form).fadeOut("slow", function() { $(this).remove(); notfound.crit_form = null; }); };
        if (this.crit_form) {
            closeCB();
        } else {
            td = $(this).parents("td");
            td.append(makeCritickerSuggestionForm(this.imdb));
            crit_form = td.find(".suggestion_form");
            setupCritFormCallbacks(crit_form, this.imdb, closeCB, $(this));
            crit_form.hide().fadeIn("slow");
            this.crit_form = crit_form;
        }
        return false;
    });
});
