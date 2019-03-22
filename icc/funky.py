from functools import wraps
from flask import request
from flask_login import current_user
from werkzeug.urls import url_parse


def is_filled(data):
    """This is a javascript-like function (in that it's obnoxious) that tests
    whether a field in a wtform is filled or not.
    """
    if not data.strip():
        return False
    if data is None:
        return False
    if data == '':
        return False
    if data == []:
        return False
    return True


def generate_next(alt_url):
    """A simple way to generate a next-url redirect."""
    redirect_url = request.args.get('next')
    if redirect_url and url_parse(redirect_url).netloc == '':
        return redirect_url
    else:
        return alt_url


def line_check(fl, ll):
    """This takes a first line and last line in a wtf form for annotating and
    returns a tuple of ints.
    """
    # technically none of this can happen anyway because of my Edit.__init__(),
    # but I'm doing this anyway.
    fl = 1 if fl < 1 else fl
    ll = 1 if ll < 1 else ll
    if ll < fl:
        fl, ll = ll, fl
    return fl, ll


def authorize(string):
    """A wrapper function to authorize a route with a wrapper."""
    def inner(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user.authorize(string)
            return f(*args, **kwargs)
        return wrapper
    return inner
