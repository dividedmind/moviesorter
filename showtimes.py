# -*- coding: utf-8 -*-

import urllib, re, time
from logging import info, debug
from datetime import datetime, timedelta

from google.appengine.api import memcache
import geonames, pytz

BASE = 'http://www.google.com/movies?hl=en&sort=3&near='
TITLE_RE = re.compile(r'mid=([^"]*?)"><b dir=ltr>(.*?)</b>(.*?)<tr><td>&nbsp;</td></tr>')
CINEMA_RE = re.compile(r'tid=([0-9a-f]*)"><b dir=ltr>(.*?)</b></a><br>.*?<br>(.*?)</font></td>')
NEXT_RE = re.compile(r'<br>Next</a>')
PLACE_RE = re.compile(r'<b>Showtimes for (.*?)</b>')
NO_SHOWTIMES = 'No showtimes were found on'

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

def movielink(baseurl, mid):
    return baseurl + "&mid=" + mid

def cinemalink(baseurl, tid):
    return baseurl + "&tid=" + tid

def get_and_decode(url):
    return decode_htmlentities(unicode(urllib.urlopen(url).read(), "latin1"))

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

            jt = CINEMA_RE.finditer(rest)
            cinemas = []
            for j in jt:
                tid = j.group(1)
                cinema = j.group(2)
                times = j.group(3).split('&nbsp; ')
                cinemas.append({'link': cinemalink(baseurl, tid), 'name': cinema, 'times': times})

            movies.append({'mid': mid, 'link': movielink(baseurl, mid), 'title': title, 'cinemas': cinemas})

        break # for debugging, don't fetch half the internet, ok
        if NEXT_RE.search(showtimes_page):
            start = start + 10
            url = baseurl + "&start=" + str(start)
        else:
            break

    return movies

def nearest_midnight(time):
    next_day = time + timedelta(days=1)
    next_day = next_day.replace(hour = 0).replace(minute = 0).replace(second = 0)
    return next_day

def find(city):
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
