# -*- coding: utf-8 -*-

from urllib import urlencode

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import showtimes

template.register_template_library('abbrev')

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render("welcome.html", {}))

class Movies(webapp.RequestHandler):
    def get(self):
        city = self.request.get('city')
        real_city = showtimes.place(city)
        if real_city:
            self.redirect(self.request.path + "?" + urlencode({'city': real_city}), permanent = True)
        else:
            self.response.out.write(template.render("movies.html", { 'city': city, 'movies': showtimes.find(city) }))

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
