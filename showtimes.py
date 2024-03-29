# -*- coding: utf-8 -*-

import urllib, re, time
from logging import info, debug
from datetime import datetime, timedelta

from google.appengine.api import memcache
from google.appengine.ext import db
import geonames, pytz

from util import get_and_decode

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'mid=([^"]*?)">(.*?)</a>(.*?)<p class=clear></div></div>')
CINEMA_RE = re.compile(r'tid=([0-9a-f]*)" id=link_1_theater_\d+>(.*?)</a></div><div class=address>.*?<a href="" class=fl target=_top></a></div></div><div class=times>(.*?)</div>')
NEXT_RE = re.compile(r'<br>Next</a>')
PLACE_RE = re.compile(r'<h1 id=title_bar>Showtimes for (.*?)</h1>')
NO_SHOWTIMES = 'No showtimes were found on'

def movielink(baseurl, mid):
    return baseurl + "&mid=" + mid

def cinemalink(baseurl, tid):
    return baseurl + "&tid=" + tid

class MovieIds(db.Model):
    title = db.StringProperty(required = True)
    
    @staticmethod
    def add(mid, title):
        record = MovieIds.get_or_insert("mid:" + mid, title = title)
        record.title = title
        debug("putting mid:" + mid + " title:" + title)
        record.put()
    
    @staticmethod
    def get_title(mid):
        debug("finding mid:" + mid)
        record = MovieIds.get_by_key_name("mid:" + mid)
        return record.title

def do_find(city):
    url = baseurl = BASE + urllib.quote(city.encode("utf-8"))

    movies = [ ]
    start = 0
    tomorrows = False
    while True:
        info("fetching " + url)
        showtimes_page = get_and_decode(url)
        if start == 0 and not tomorrows:
            # if no showtimes for today, try tomorrow's
            try:
                foo = showtimes_page.index(NO_SHOWTIMES)
                info("No showtimes for today for " + city + ", trying tomorrow")
                url = baseurl = baseurl + "&date=1"
                tomorrows = True
                continue
            except:
                pass

        it = TITLE_RE.finditer(showtimes_page)
        for i in it:
            mid = i.group(1)
            title = i.group(2)
            rest = i.group(3)
            info("No showtimes for today for " + city + ", trying tomorrow")

            jt = CINEMA_RE.finditer(rest)
            cinemas = []
            for j in jt:
                tid = j.group(1)
                cinema = j.group(2)
                times = j.group(3).split('&nbsp; ')
                cinemas.append({'link': cinemalink(baseurl, tid), 'name': cinema, 'times': times})

            MovieIds.add(mid, title)
            movies.append({'mid': mid, 'link': movielink(baseurl, mid), 'title': title, 'cinemas': cinemas})

        if NEXT_RE.search(showtimes_page):
            start = start + 10
            url = baseurl + "&start=" + str(start)
        else:
            break

    return movies

def city_movie_link(city, mid):
    baseurl = BASE + urllib.quote(city.encode("utf-8"))
    return movielink(baseurl, mid)

def nearest_midnight(time):
    next_day = time + timedelta(days=1)
    next_day = next_day.replace(hour = 0).replace(minute = 0).replace(second = 0)
    return next_day

def find(city):
    if city == 'enh2009':
        return read_enh2009()
    city_enc = city.encode('utf-8')
    result = memcache.get(city_enc, namespace = "showtimes")
    if not result:
        result = do_find(city)
        tz = geonames.timezone(city)
        now = pytz.utc.localize(datetime.utcnow())
        midnight = cache_timeout = nearest_midnight(now)
        if tz:
            now = now.astimezone(tz)
            midnight = nearest_midnight(now)
            cache_timeout = midnight.astimezone(pytz.utc)

        cache_timeout_epoch = time.mktime(cache_timeout.timetuple())
        debug("cache for " + city + " will expire at " + midnight.ctime() + " local, which is " + cache_timeout.ctime() + " UTC / epoch = " + str(cache_timeout_epoch))

        memcache.set(city_enc, result, cache_timeout_epoch, namespace = "showtimes")

    return result

def read_enh2009():
    debug("reading enh")
    f = open('enh2009.txt', 'r')
    movies = []
    for line in f:
        enhid, title = line.split(":::")
        m = {'mid': "enh2009:" + enhid, 'link': "http://www.enh.pl/film.do?id=" + enhid, 'title': title}
        debug("got movie: " + str(m))
        movies.append(m)
    return movies

def get_place(typed):
    if typed == 'enh2009':
        return typed
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
