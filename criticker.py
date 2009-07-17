# -*- coding: utf-8 -*-

import re, urllib

from google.appengine.ext import db
from google.appengine.api import users

from mechanize import Browser

class WrongPassword(Exception):
    pass

class Session:
    def __init__(self, user, passwd):
        self.agent = br = Browser()

        br.open('http://www.criticker.com/signin.php')
        br.select_form('signinform')
        br['si_password'] = passwd
        br['si_username'] = user
        res = br.submit().read()
        try:
            foo = res.index('index.php')
        except:
            raise WrongPassword(user + ":" + passwd)

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

def set_credentials(username, password):
    s = Session(username, password)
    CritickerCredentials.set(username, password)
