# -*- coding: utf-8 -*-

import re
from logging import debug, warn, info

from google.appengine.ext import db
from google.appengine.api import users

from imdb import IMDb

from memoize import gaecache

ia = IMDb(accessSystem = 'mobile')

def massage_title(original_title):
    # hacks, heuristics &c go here
    return re.sub(r'^(.*), The', r'The \1', original_title)

@gaecache()
def fetch_info(movieID):
    im = ia.get_movie(movieID, info = 'main')
    return im

@gaecache()
def best_guess(title):
    title = massage_title(title)
    im = ia._search_movie(title, results = 1)
    if im:
        return im[0][0]
    else:
        return None

def massage_imdbid(imdb):
    IMDB_RE = re.compile(r'^((http://)?((www\.)?imdb\.com)?/?title/)?/?(tt)?(\d{7})(/.*|$)')
    match = IMDB_RE.match(imdb)
    if match:
        return match.group(6)
    else:
        return None

def mid_valid(mid):
    MID_RE = re.compile("^[a-f0-9]+$")
    return MID_RE.match(mid)

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
    def register(mid, imdb):
        """ registers vote. logic:
        - massage imdb id, bail out if invalid
        - if user is admin:
            - save admin vote
            - remove vote tally from the database
        - else tally vote
        """
        if not mid_valid(mid):
            warn("invalid mid [" + mid + "] submitted, discarding")
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

def imdbid_for_movie(movie):
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
    return [False, best_guess(title)]

def vote(mid, imdb):
    Vote.register(mid, imdb)

def imdbize(movies):
    for m in movies:
        [authoritative, imdbid] = imdbid_for_movie(m)
        if imdbid:
            m['imdb'] = fetch_info(str(imdbid))
        m['imdb_confirmed'] = authoritative
    return movies
