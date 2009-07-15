# -*- coding: utf-8 -*-

from google.appengine.ext import webapp

register = webapp.template.create_template_register()

@register.filter
def abbrev(name):
    return ''.join([word[0].upper() for word in name.split()])
