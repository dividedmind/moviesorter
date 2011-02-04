# -*- coding: utf-8 -*-

import urllib
from logging import debug

from django.utils import simplejson
import pytz

from memoize import gaecache

@gaecache()
def find(place):
    BASE_URL = "http://ws.geonames.org/searchJSON?maxRows=1&q="
    while True:
        url = BASE_URL + urllib.quote(place.encode('utf-8'))
        response = unicode(urllib.urlopen(url).read(), 'utf-8')
        result = simplejson.loads(response)
        # TODO: not cache if no 'totalResultsCount'
        if 'totalResultsCount' in result and result['totalResultsCount'] > 0:
            return result['geonames'][0]
        else:
            # try to fix the placename
            # (heuristics, hacks, etc. go here)

            # Irish counties
            newname = place.replace("Co.", "County")
            if newname != place:
                place = newname
            else:
                return None

@gaecache()
def timezone(place):
    BASE_URL = "http://ws.geonames.org/timezoneJSON?"
    place = find(place)
    if not place:
        return None

    url = BASE_URL + urllib.urlencode({'lat': place['lat'], 'lng': place['lng']})
    response = unicode(urllib.urlopen(url).read(), 'utf-8')
    result = simplejson.loads(response)

    if result:
        timezoneId = result['timezoneId']
        return pytz.timezone(timezoneId)
    else:
        return None
