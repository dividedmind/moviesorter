# -*- coding: utf-8 -*-

import urllib, re
from logging import info, debug

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'<tr valign=top>.*?<a href="(/movies\?hl=en[^"]*?&mid=[^"]*?)"><b dir=ltr>(.*?)</b>.*?</tr>')

def find(city):
    url = BASE + urllib.quote(city)
    info("fetching " + url)
    showtimes_page = urllib.urlopen(url).read()

    movies = [ ]
    it = TITLE_RE.finditer(showtimes_page)
    for i in it:
        movies.append({'link': 'http://www.google.com' + i.group(1), 'title': i.group(2)})

    debug("movies: " + unicode(movies))

    return movies
