import time

from flask import request
from flask_login import current_user, login_user

from icc.api import api

from icc.models.user import User

@api.route('/time')
def get_time():
    return {'time': time.time()}

@api.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(email=request.json['email']).first()

    if user and user.locked:
        return {'success': False, 'flash': "That account is locked."}
    elif user is None or not user.check_password(request.json['password']):
        return {'success': False, 'flash': "Invalid email or password"}

    return {'success': True}

@api.route('/current_user')
def get_current_user():
    if current_user.is_authenticated:
        return {'user': current_user.displayname}
    else:
        return {'user': None}
