"""This file, cheekily named funky.py, is just a smörgåsbord of useful helper
functions. I'm not even sure that I really want all of them to continue to
exist, but they will for now.

The most essential two functions are generate_next and authorize.
"""
import re
from functools import wraps
from flask import request
from flask_login import current_user
from werkzeug.urls import url_parse
from icc import classes


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


LINKABLE = re.compile(r'\[\[[a-zA-Z]*?:.*?\]\]')

def proc_links(text):
    """Process text to turn double-bracketted icc-link expressions into actual
    href's.

    This method is not trivial and relies on a special attr/mixin.
    """
    newtext = []
    for match in re.finditer(LINKABLE, text):
        idx = match.span()
        if newtext:
            # I rather dislike this method, but, we have to first reverse find
            # within text from the start of this match to the begginning of text
            # the first (or rather, last) closing double brackets. We add 2
            # because there are two brackets so that when we slice, we slice
            # from just after the double close brackets. Then we slice the text
            # from that point to the beginning of the current match and append
            # it to our new text. This is only once we've had one link. The
            # first link is in the else. It's just all the text preceding this.
            leftoff = text[:idx[0]].rfind(']]') + 2
            missing = text[leftoff:idx[0]]
            newtext.append(missing)
        else:
            newtext.append(text[:idx[0]])

        try:
            unbracketted = text[idx[0]+2:idx[1]-2]
            colon = unbracketted.index(':')
            cls = unbracketted[:colon]
            ident = unbracketted[colon+1:]
            if cls in classes and hasattr(classes[cls], 'link'):
                href = classes[cls].link(ident)
                newtext.append(href)
            else:
                newtext.append(ident)
        except:
            newtext.append(text[idx[0]:idx[1]])
    newtext.append(text[match.span()[1]:])
    return ''.join(newtext)
