from functools import wraps
from flask import request
from flask_login import current_user
from werkzeug.urls import url_parse


# This method is used to run through all the lines for a read view and convert/
# prep them to be shown: (a) converts underscores to <em>/</em> tags, and (b)
# opens and closes surrounding <em></em> tags on lines that need it so that the
# tags don's span multiple levels in the DOM and throw everything into a tizzy.
# It also allows me to display an arbitrary number of lines perfectly.
def preplines(lines):
    us = False

    for i, line in enumerate(lines):

        if '_' in lines[i].line:
            newline = []
            for c in lines[i].line:
                if c == '_':
                    if us:
                        newline.append('</em>')
                        us = False
                    else:
                        newline.append('<em>')
                        us = True
                else:
                    newline.append(c)
            lines[i].line = ''.join(newline)

        if line.em_status.enum == 'oem':
            lines[i].line = lines[i].line + '</em>'
        elif line.em_status.enum == 'cem':
            lines[i].line = '<em>' + lines[i].line
        elif line.em_status.enum == 'em':
            lines[i].line = '<em>' + lines[i].line + '</em>'


def is_filled(data):
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
    redirect_url = request.args.get('next')
    if redirect_url and url_parse(redirect_url).netloc == '':
        return request.args.get('next')
    elif request.referrer:
        return request.referrer
    else:
        return alt_url


def line_check(fl, ll):
    # technically none of this can happen anyway because of my Edit.__init__(),
    # but I'm doing this anyway.
    fl = 1 if fl < 1 else fl
    ll = 1 if ll < 1 else ll
    if ll < fl:
        fl, ll = ll, fl
    return fl, ll


def authorize(string):
    def inner(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user.authorize(string)
            return f(*args, **kwargs)
        return wrapper
    return inner
