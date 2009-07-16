# -*- coding: utf-8 -*-

import re
from logging import debug

from imdb import IMDb

from memoize import gaecache

ia = IMDb()

def massage_title(original_title):
    # hacks, heuristics &c go here
    return re.sub(r'^(.*), The', r'The \1', original_title)

@gaecache()
def best_guess(title):
    title = massage_title(title)
    im = ia.search_movie(title)
    if im:
        return im[0]
    else:
        return None

def imdbize(movies):
    for m in movies:
        im = best_guess(m['title'])
        debug("imdb for " + m['title'] + ": " + unicode(im))
    return movies
