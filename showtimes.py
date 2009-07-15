# -*- coding: utf-8 -*-

import urllib, re
from logging import info, debug

from google.appengine.api import memcache

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'mid=([^"]*?)"><b dir=ltr>(.*?)</b>(.*?)<tr><td>&nbsp;</td></tr>')
CINEMA_RE = re.compile(r'tid=([0-9a-f]*)"><b dir=ltr>(.*?)</b></a><br>.*?<br>(.*?)</font></td>')
NEXT_RE = re.compile(r'<br>Next</a>')
PLACE_RE = re.compile(r'<b>Showtimes for (.*?)</b>')

def movielink(city, mid):
    return "http://www.google.com/movies?hl=en&near=" + urllib.quote(city) + "&mid=" + mid

def cinemalink(tid):
    return "/movies?hl=en&tid=" + tid

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
        cinemas = []
        for j in jt:
            tid = j.group(1)
            cinema = j.group(2)
            times = j.group(3).split('&nbsp; ')
            cinemas.append({'link': cinemalink(tid), 'name': cinema, 'times': times})

        movies.append({'link': movielink(city, mid), 'title': title, 'cinemas': cinemas})

    debug("movies: " + unicode(movies))

    return movies

def get_place(typed):
    reloc = memcache.get(typed, namespace = "places")
    if reloc:
        return reloc

    url = BASE + urllib.quote(typed)
    showtimes_page = urllib.urlopen(url).read()
    real = PLACE_RE.search(showtimes_page).group(1)
    memcache.set(typed, real, namespace = "places")
    return real

def place(typed):
    reloc = get_place(typed)
    if reloc == typed:
        return None
    else:
        return reloc
