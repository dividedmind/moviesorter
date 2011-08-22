# -*- coding: utf-8 -*-

import re
from logging import debug, warn, info
from urllib import URLopener

from google.appengine.ext import db
from google.appengine.api import users, memcache

from imdb import IMDb

from memoize import gaecache
from util import decode_htmlentities

ia = IMDb(accessSystem = 'mobile')

MOVIE_URL = 'http://m.imdb.com/title/tt%s/'
TITLE_RE = re.compile(r"<h1>(.*?) \(\d{4}.*?\)</h1>")
RATING_RE = re.compile(r'<strong>(.*?)</strong>')

class IMDbURLopener(URLopener):
    version = 'Mozilla/5.0'

Opener = IMDbURLopener()

def massage_title(original_title):
    # hacks, heuristics &c go here
    title = re.sub(r'^(.*), The', r'The \1', original_title)
    title = re.sub(r' \(projekcje [35]D\)$', '', title)
    title = re.sub(r' [35]D$', '', title)
    return title.strip()

def load_url(url):
    return decode_htmlentities(unicode(Opener.open(url).read(), "latin1"))

def fetch_info(movieID, fetch):
    im = memcache.get(movieID, namespace = 'imdb_info')
    if im:
        return im
    if not fetch:
        return None
    
    url = MOVIE_URL % movieID
    movie_page = load_url(url)
    debug(movie_page)
    title = TITLE_RE.search(movie_page).group(1)
    if not title:
        warn("Could not find imdb title for movie id %s" % movieID)
    match = RATING_RE.search(movie_page)
    rating = None
    if match:
        rating = float(match.group(1))
    if not rating:
        warn("Could not find imdb rating for movie id %s" % movieID)
    im = {
        'title': title,
        'rating': rating,
        'movieID': movieID
    }
    memcache.set(movieID, im, namespace = 'imdb_info')
    return im

def best_guess(title, fetch):
    result = memcache.get(title, namespace = 'imdb_title')
    if result != None:
        return result
    if not fetch:
        return None
    
    title = massage_title(title)
    im = ia._search_movie(title, results = 1)
    if im:
        result = im[0][0]
    else:
        result = 0
    
    memcache.set(title, result, namespace = 'imdb_title')
    return result

def massage_imdbid(imdb):
    IMDB_RE = re.compile(r'^((http://)?((www\.)?imdb\.com)?/?title/)?/?(tt)?(\d{7})(/.*|$)')
    match = IMDB_RE.match(imdb)
    if match:
        return match.group(6)
    else:
        return None

def mid_valid(mid):
    MID_RE = re.compile("^[a-f0-9]+$")
    if MID_RE.match(mid):
        return mid

    ENH_RE = re.compile("^http://www.enh.pl/film.do\?id=(\d+)$")
    m = ENH_RE.match(mid)
    if m:
        return "enh2009:" + m.group(1)

class Vote(db.Model):
    imdb = db.StringProperty(required = True)

    def __init__(self, *args, **kargs):
        if len(args) == 2 and len(kargs) == 0:
            votes, imdbid = args
            key_name = "anonymous"
            user = users.get_current_user()
            if user:
                key_name = "uid:" + user.user_id()
            db.Model.__init__(self, parent = votes, key_name = key_name, imdb = imdbid)
        else:
            return db.Model.__init__(self, *args, **kargs)

    @staticmethod
    def get_user_vote(votes):
        user = users.get_current_user()
        if user:
            uid = user.user_id()
            return Vote.get_by_key_name("uid:" + uid, votes)

    @staticmethod
    def get_anonymous_or_user_vote(votes):
        user = users.get_current_user()
        if user:
            return Vote.get_by_key_name("uid:" + user.user_id(), votes)
        else:
            return Vote.get_by_key_name("anonymous", votes)

    @staticmethod
    def get_admin_vote(mid):
        return Vote.get_by_key_name("admin:mid:" + mid);

    @staticmethod
    def tally_vote(mid, imdbid):
        """ logic:
            - retrieve vote tally
            - retrieve previous vote
            - if it's there, subtract it from the tally
            - update the vote
            - add it to tally
            - resort the tally
            - save tally
        """
        uid = "anonymous"
        user = users.get_current_user()
        if user:
            uid = user.user_id()
        info("registering vote for " + mid + "->" + imdbid + " from " + uid)
        votes = Votes.get_by_mid(mid)
        if not votes:
            votes = Votes(mid)
        vote = Vote.get_anonymous_or_user_vote(votes)
        if vote:
            votes.subtract(imdbid)
        else:
            vote = Vote(votes, imdbid)
        vote.imdb = imdbid
        votes.add(imdbid)
        votes.put()
        vote.put()

    @staticmethod
    def register(given_mid, imdb):
        """ registers vote. logic:
        - massage imdb id, bail out if invalid
        - if user is admin:
            - save admin vote
            - remove vote tally from the database
        - else tally vote
        """
        mid = mid_valid(given_mid)
        if not mid:
            warn("invalid mid [" + given_mid + "] submitted, discarding")
            return
        imdbid = massage_imdbid(imdb)
        if not imdbid:
            warn("invalid imdbid [" + imdb + "] submitted, discarding")
            return

        if users.is_current_user_admin():
            info("current user is admin, saving authoritative mapping " + mid + "->" + imdbid)
            v = Vote.get_or_insert("admin:mid:" + mid, imdb = imdbid)
            v.imdb = imdbid
            v.put()

        db.run_in_transaction(Vote.tally_vote, mid, imdbid)

class Votes(db.Model):
    imdbs = db.StringListProperty(required = True)
    votes = db.ListProperty(long)

    @staticmethod
    def get_by_mid(mid):
        kname = "mid:" + mid
        debug("getting votes by key name \"" + kname + "\"")
        return Votes.get_by_key_name(kname)

    def __init__(self, *args, **kargs):
        if len(args) == 1 and len(kargs) == 0:
            return db.Model.__init__(self, key_name = "mid:" + args[0])
        else:
            return db.Model.__init__(self, *args, **kargs)

    def add(self, imdbid):
        try:
            index = self.imdbs.index(imdbid)
            self.votes[index] += 1
            if index > 0:
                if self.votes[index - 1] < self.votes[index]:
                    self.swap(index, index - 1)
        except:
            self.imdbs.append(imdbid)
            self.votes.append(1)
        debug("added vote for " + imdbid + " at " + self.key().name() + ", current votes: " + ", ".join(self.imdbs) + "[" + ", ".join(map(lambda v: str(v), self.votes)) + "]")

    def subtract(self, imdbid):
        try:
            index = self.imdbs.index(imdbid)
            self.votes[index] -= 1
            if self.votes[index] == 0:
                del self.votes[index]
                del self.imdbs[index]
            elif index < len(self.votes) - 1:
                if self.votes[index + 1] > self.votes[index]:
                    self.swap(index, index + 1)
        except:
            self.imdbs.append(imdbid)
            self.votes.append(1)
        debug("subtracted vote for " + imdbid + " at " + self.key().name() + ", current votes: " + ", ".join(self.imdbs) + "[" + ", ".join(map(lambda v: str(v), self.votes)) + "]")

    def swap(self, a, b):
        if a == b:
            return
        avotes = self.votes[a]
        aimdb = self.imdbs[a]
        self.votes[a] = self.votes[b]
        self.imdbs[a] = self.imdbs[b]
        self.votes[b] = avotes
        self.imdbs[b] = aimdb

def imdbid_for_movie(movie, fetch):
    """
        get imdbid for movie.
        returns [authoritative, imdbid], where authoritative is false iff the match was guessed

        logic:
        - if user is logged in and has voted, return their vote
        - else if admin has voted, return admin vote
        - else return best vote
        - if no votes, return best guess
    """
    mid = movie['mid']
    debug("searching for votes on " + mid)
    title = movie['title']
    votes = Votes.get_by_mid(mid)
    admin_vote = Vote.get_admin_vote(mid)
    if votes:
        their_vote = Vote.get_user_vote(votes)
        if their_vote:
            debug("user has voted for " + title + ", returning their vote")
            return [True, their_vote.imdb]
    if admin_vote:
        debug("returning admin vote")
        return [True, admin_vote.imdb]
    if votes:
        debug("user has not voted or is not logged in, returning best vote for " + title)
        return [True, votes.imdbs[0]]

    debug("trying to guess")
    return [False, best_guess(title, fetch)]

def vote(mid, imdb):
    Vote.register(mid, imdb)

def imdbize(movies, fetch = False):
    for m in movies:
        m['fetch_required'] = False
        [authoritative, imdbid] = imdbid_for_movie(m, fetch)
        if imdbid == None:
            m['fetch_required'] = True
        if imdbid:
            imdb = fetch_info(str(imdbid), fetch)
            if imdb:
                m['imdb'] = imdb
            else:
                m['fetch_required'] = True
        m['imdb_confirmed'] = authoritative
    return movies
