# -*- coding: utf-8 -*-
"""
a decorator to use memcache on google appengine.
optional arguments:
  `key`: the key to use for the memcache store
  `time`: the time to expiry sent to memcache

if no key is given, the function name, args, and kwargs are
used to create a unique key so that the same function can return
different results when called with different arguments (as
expected).

usage:
NOTE: actual usage is simpler as:
@gaecache()
def some_function():
...

but doctest doesnt seem to like that.

    >>> import time

    >>> def slow_fn():
    ...    time.sleep(1.1)
    ...    return 2 * 2
    >>> slow_fn = gaecache()(slow_fn)

this run take over a second.
    >>> t = time.time()
    >>> slow_fn(), time.time() - t > 1
    (4, True)

this grab from cache in under .01 seconds
    >>> t = time.time()
    >>> slow_fn(), time.time() - t < .01
    (4, True)

modified from
http://code.activestate.com/recipes/466320/
and
http://code.activestate.com/recipes/325905/

--
from http://hackmap.blogspot.com/2008/10/appengine-memcache-memoize-decorator.html
"""

from google.appengine.api import memcache
import logging
import pickle

class gaecache(object):
    """
    memoize decorator to use memcache with a timeout and an optional key.
    if no key is given, the func_name, args, kwargs are used to create a key.
    """
    def __init__(self, time=0, key=None):
        self.time = time
        self.key  = key

    def __call__(self, f):
        def func(*args, **kwargs):
            if self.key is None:
                t = (f.func_name, args, kwargs.items())
                try:
                    hash(t)
                    key = t
                except TypeError:
                    try:
                        key = pickle.dumps(t)
                    except pickle.PicklingError:
                        logging.warn("cache FAIL:%s, %s", args, kwargs)
                        return f(*args, **kwargs)
            else:
                key = self.key

            data = memcache.get(key)
            if data is not None:
                logging.info("cache HIT: key:%s, args:%s, kwargs:%s", key, args, kwargs)
                return data

            logging.warn("cache MISS: key:%s, args:%s, kwargs:%s", key, args, kwargs)
            data = f(*args, **kwargs)
            memcache.set(key, data, self.time)
            return data

        func.func_name = f.func_name
        return func
