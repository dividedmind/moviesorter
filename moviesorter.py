# -*- coding: utf-8 -*-

from urllib import urlencode
from logging import info, debug
from datetime import datetime

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import showtimes, geonames
import imdbizator
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
        self.response.out.write(template.render(templ, arguments))

class MainPage(RequestHandler):
    def get(self):
        self.render("welcome.html", {})

def sort_by_imdb(movies):
    return sorted(movies, key = lambda m: 'imdb' in m and m['imdb']['rating'] or 0.0, reverse = True)

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

application = webapp.WSGIApplication(
                                     [
                                        ('/', MainPage),
                                        ('/movies', Movies),
                                        ('/imdb_suggest', ImdbSuggest),
                                     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
