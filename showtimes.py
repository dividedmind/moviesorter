# -*- coding: utf-8 -*-

import urllib, re
from logging import info, debug

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'mid=([^"]*?)"><b dir=ltr>(.*?)</b>(.*?)<tr><td>&nbsp;</td></tr>')
CINEMA_RE = re.compile(r'tid=([0-9a-f]*)"><b dir=ltr>(.*?)</b></a><br>.*?<br>(.*?)</font></td>')

def movielink(city, mid):
    return "http://www.google.com/movies?hl=en&near=" + urllib.quote(city) + "&mid=" + mid

def find(city):
    url = BASE + urllib.quote(city)
    info("fetching " + url)
    showtimes_page = urllib.urlopen(url).read()

    movies = [ ]
    it = TITLE_RE.finditer(showtimes_page)
    for i in it:
        mid = i.group(1)
        title = i.group(2)
        rest = i.group(3)

        jt = CINEMA_RE.finditer(rest)
        showtimes = []
        for j in jt:
            tid = j.group(1)
            cinema = j.group(2)
            times = j.group(3).split('&nbsp; ')
            for t in times:
                showtimes.append({'time': t})

        movies.append({'link': movielink(city, mid), 'title': title, 'showtimes': showtimes})

    debug("movies: " + unicode(movies))

    return movies
