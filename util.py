# -*- coding: utf-8 -*-

import urllib, re

def substitute_entity(match):
    ent = match.group(3)

    if match.group(1) == "#":
        if match.group(2) == '':
            return unichr(int(ent))
        elif match.group(2) == 'x':
            return unichr(int('0x'+ent, 16))
    else:
        return match.group()

def decode_htmlentities(string):
    entity_re = re.compile(r'&(#?)(x?)(\w+);')
    return entity_re.subn(substitute_entity, string)[0]

def get_and_decode(url):
    return decode_htmlentities(unicode(urllib.urlopen(url).read(), "latin1"))
