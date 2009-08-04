# -*- coding: utf-8 -*-

import re, urllib
from logging import debug, info

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import users

from imdbizator import massage_imdbid
from mechanize import Browser
from memoize import gaecache
from util import get_and_decode, decode_htmlentities

def movie_url(critID):
    return 'http://www.criticker.com/film/' + critID + "/"

@gaecache()
def check_match(critID, imdbid):
    debug("checking match for " + imdbid + " at " + critID)
    lookingfor = 'http://www.imdb.com/title/tt' + imdbid
    result = get_and_decode(movie_url(critID))
    try:
        foo = result.index(lookingfor)
        return True
    except:
        return False

def massage_critid(crit):
    CRIT_RE = re.compile(r'^((http://)?((www\.)?criticker\.com)?/?film/)?/?(.*?)(/|$)')
    match = CRIT_RE.match(crit)
    if match:
        return match.group(5)
    else:
        return None

def try_match(crit, imdb):
    imdb = massage_imdbid(imdb)
    crit = massage_critid(crit)
    if not (imdb and crit):
        return None
    if check_match(crit, imdb):
        info("found imdb to criticker mapping from " + imdb + " to " + crit)
        icm = ImdbCritickerMapping.get_or_insert("imdb:" + imdb, critID = crit)
        icm.critID = crit
        icm.put()
        return crit
    else:
        return None

@gaecache()
def search_by_title(title):
    info("searching for imdb->criticker mapping for " + title)
    BASE_URL = 'http://www.criticker.com/?st=movies&g=Go&h='
    RESULT_RE = re.compile(r'<div class=\'sr_result_name\'><a href=\'http://www.criticker.com/film/(.*?)/\'>')
    FILM_RE = re.compile(r'http://www.criticker.com/film/(.*?)/')
    query_url = BASE_URL + urllib.quote(title.encode('utf-8'))
    cnn = urllib.urlopen(query_url)
    goturl = cnn.geturl()
    if goturl != query_url:
        debug('criticker redirected us to ' + goturl + ', trying to make odds of it')
        match = FILM_RE.search(goturl)
        if match:
            return [match.group(1)]
        return 0

    result = decode_htmlentities(unicode(cnn.read(), "latin1"))

    ids_to_try = set()

    for match in RESULT_RE.finditer(result):
        ids_to_try.add(match.group(1))

    return ids_to_try

def search_by_imdb(imdb):
    ids_to_try = search_by_title(imdb['title'])
    if ids_to_try == 0:
        return None
    for i in ids_to_try:
        m = try_match(i, imdb.movieID)
        if m:
            return m

class ImdbCritickerMapping(db.Model):
    critID = db.StringProperty(required = True)

    @staticmethod
    def find(imdb):
        mapping = ImdbCritickerMapping.get_by_key_name("imdb:" + imdb.movieID)
        if mapping:
            debug("returning known imdb to criticker mapping from " + imdb.movieID + " to " + mapping.critID)
            return mapping.critID

        if imdb:
            return search_by_imdb(imdb)

class WrongPassword(Exception):
    pass

PSI_RE = re.compile(r'<font class=\'pti_font\'>(\d{1,3})</font>')
class Session:
    def __init__(self, user, passwd):
        self.agent = br = Browser()
        self.user = user

        br.open('http://www.criticker.com/signin.php')
        br.select_form('signinform')
        br['si_password'] = passwd
        br['si_username'] = user
        res = br.submit().read()
        try:
            foo = res.index('index.php')
        except:
            raise WrongPassword(user + ":" + passwd)
        self.flurl = 'http://www.criticker.com/?fl&view=prs'

    @staticmethod
    def for_current_user():
        creds = CritickerCredentials.get_for_current_user()
        if not creds:
            return None
        return Session(creds.username, creds.password)

    def get_data_for_movie(self, movie):
        if not 'imdb' in movie:
            return None
        critID = ImdbCritickerMapping.find(movie['imdb'])
        
        if not critID:
            return None

        result = memcache.get(critID, "criticker:" + self.user)
        if result:
            return result

        res = self.agent.open(movie_url(critID)).read()
        match = PSI_RE.search(res)
        data = {'critID': critID}
        if match:
            data['rating'] = match.group(1)
        else:
            data['rating'] = '???'
        memcache.set(critID, data, 3600, namespace = "criticker:" + self.user)
        return data

    def get_tiers(self):
        tiers = memcache.get("tiers", namespace = "criticker:" + self.user)
        if tiers:
            return tiers

        page = 1
        baseurl = self.flurl + "&page="
        PAGES_RE = re.compile(r'Page 1 of (\d+)')
        pages = None
        tiers = []
        while True:
            content = self.agent.open(baseurl + str(page)).read()
            if not pages:
                pages = int(PAGES_RE.search(content).group(1))
            TIER_RE = re.compile(r'Tier (\d{1,2}) Films</div>.*?class=\'score_[a-z]+\'>(\d{1,3})', flags = re.S)
            for m in TIER_RE.finditer(content):
                tier = int(m.group(1))
                score = int(m.group(2))
                debug("found tier " + str(tier) + " at score " + str(score))
                while len(tiers) < (11 - tier):
                    tiers.append(score)
            page += 1
            if page > pages:
            	break

        debug("final tiers: " + str(tiers))
        memcache.set("tiers", tiers, namespace = "criticker:" + self.user)
        return tiers

class CritickerCredentials(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)

    @staticmethod
    def set(username, password):
        user = users.get_current_user()
        if not user:
            return
        creds = CritickerCredentials.get_or_insert("user:" + user.user_id(), username = username, password = password)
        creds.username = username
        creds.password = password
        creds.put()

    @staticmethod
    def get_username():
        creds = CritickerCredentials.get_for_current_user()
        if not creds:
            return None
        username = creds.username
        return username

    @staticmethod
    def get_for_current_user():
        user = users.get_current_user()
        if not user:
            return None
        return CritickerCredentials.get_by_key_name("user:"  + user.user_id())

def set_credentials(username, password):
    s = Session(username, password)
    CritickerCredentials.set(username, password)

def get_username():
    return CritickerCredentials.get_username()

def forget_credentials():
    creds = CritickerCredentials.get_for_current_user()
    creds.delete()

def ize(movies):
    session = Session.for_current_user()
    if not session:
        return movies

    tiers = session.get_tiers()
    for m in movies:
        m['criticker'] = session.get_data_for_movie(m)
        try:
            foo = int(m['criticker']['rating'])
        except:
            if 'imdb' in m:
                rating = m['imdb'].get('rating')
                if rating:
                    m['synthetic_criticker'] = synthesize(rating, tiers)

    return movies

def synthesize(ten_ranking, tiers):
    """ tiers are [best score for tier 10, bsft9, ..., bsft1 """
    base = 10 - int(ten_ranking)
    delta = ten_ranking % 1
    value = int(round(tiers[base] + (tiers[base - 1] - tiers[base]) * delta))
    return value
