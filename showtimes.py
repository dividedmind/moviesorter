# -*- coding: utf-8 -*-

import urllib, re
from logging import info, debug

from google.appengine.api import memcache

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'mid=([^"]*?)"><b dir=ltr>(.*?)</b>(.*?)<tr><td>&nbsp;</td></tr>')
CINEMA_RE = re.compile(r'tid=([0-9a-f]*)"><b dir=ltr>(.*?)</b></a><br>.*?<br>(.*?)</font></td>')
NEXT_RE = re.compile(r'<br>Next</a>')
PLACE_RE = re.compile(r'<b>Showtimes for (.*?)</b>')

def substitute_entity(match):
    ent = match.group(3)

    if match.group(1) == "#":
        if match.group(2) == '':
            return unichr(int(ent))
        elif match.group(2) == 'x':
            return unichr(int('0x'+ent, 16))
    else:
        return match.group()

def decode_htmlentities(string):
    entity_re = re.compile(r'&(#?)(x?)(\w+);')
    return entity_re.subn(substitute_entity, string)[0]

def movielink(city, mid):
    return "http://www.google.com/movies?hl=en&near=" + urllib.quote(city.encode('utf-8')) + "&mid=" + mid

def cinemalink(tid):
    return "/movies?hl=en&tid=" + tid

def get_and_decode(url):
    return decode_htmlentities(unicode(urllib.urlopen(url).read(), "latin1"))

def find(city):
    url = BASE + urllib.quote(city.encode("utf-8"))
    info("fetching " + url)
    showtimes_page = get_and_decode(url)

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
    typed = typed.encode("utf-8")
    reloc = memcache.get(typed, namespace = "places")
    if reloc:
        return reloc

    url = BASE + urllib.quote(typed)
    showtimes_page = get_and_decode(url)
    real = PLACE_RE.search(showtimes_page).group(1)
    memcache.set(typed, real, namespace = "places")
    return real

def place(typed):
    reloc = get_place(typed)
    if reloc == typed:
        return None
    else:
        return reloc
