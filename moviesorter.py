# -*- coding: utf-8 -*-

from urllib import urlencode
from logging import info, debug
from datetime import datetime

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import showtimes, geonames
import imdbizator, criticker
from imdbizator import imdbize

template.register_template_library('abbrev')

class RequestHandler(webapp.RequestHandler):
    def render(self, templ, arguments):
        user = users.get_current_user()
        arguments['user' ] = user
        if user:
            arguments['logout'] = users.create_logout_url(self.request.url)
        else:
            arguments['login'] = users.create_login_url(self.request.url)
        arguments['criticker_errors'] = self.request.get('criticker_errors')
        self.response.out.write(template.render(templ, arguments))

class MainPage(RequestHandler):
    def get(self):
        self.render("welcome.html", {})

def sort_by_imdb(movies):
    return sorted(movies, key = lambda m: 'imdb' in m and m['imdb'].get('rating') or 0.0, reverse = True)

class Movies(RequestHandler):
    def get(self):
        city = self.request.get('city')
        real_city = showtimes.place(city)
        if real_city:
            self.redirect(self.request.path + "?" + urlencode({'city': real_city.encode('utf-8')}), permanent = True)
        else:
            tz = geonames.timezone(city)
            if tz:
                debug("timezone for " + city + ": "  + unicode(tz) + ", current time:" + unicode(tz.localize(datetime.utcnow())))
            sts = sort_by_imdb(imdbize(showtimes.find(city)))
            self.render("movies.html", { 'city': city, 'movies': sts })

class ImdbSuggest(webapp.RequestHandler):
    def post(self):
        mid = self.request.get('mid')
        imdb = self.request.get('imdb')
        imdbizator.vote(mid, imdb)

class Criticker(webapp.RequestHandler):
    def post(self):
        city = self.request.get('city')
        params = {'city': city.encode('utf-8')}
        username = self.request.get('username')
        password = self.request.get('password')
        try:
            criticker.set_credentials(username, password)
        except criticker.WrongPassword:
            params['criticker_errors'] = "Wrong username and password."
        self.redirect("/movies?" + urlencode(params))

application = webapp.WSGIApplication(
                                     [
                                        ('/', MainPage),
                                        ('/movies', Movies),
                                        ('/imdb_suggest', ImdbSuggest),
                                        ('/criticker', Criticker),
                                     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
