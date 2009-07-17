# -*- coding: utf-8 -*-

import re, urllib

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
