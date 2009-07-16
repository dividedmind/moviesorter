# -*- coding: utf-8 -*-

from urllib import urlencode
from logging import info, debug
from datetime import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import showtimes, geonames
from imdbizator import imdbize

template.register_template_library('abbrev')

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render("welcome.html", {}))

class Movies(webapp.RequestHandler):
    def get(self):
        city = self.request.get('city')
        real_city = showtimes.place(city)
        if real_city:
            self.redirect(self.request.path + "?" + urlencode({'city': real_city.encode('utf-8')}), permanent = True)
        else:
            tz = geonames.timezone(city)
            if tz:
                debug("timezone for " + city + ": "  + unicode(tz) + ", current time:" + unicode(tz.localize(datetime.utcnow())))
            sts = imdbize(showtimes.find(city))
            self.response.out.write(template.render("movies.html", { 'city': city, 'movies': sts }))

application = webapp.WSGIApplication(
                                     [
                                        ('/', MainPage),
                                        ('/movies', Movies)
                                     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
