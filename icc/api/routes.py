import time

from flask import request

from icc.api import api

@api.route('/time')
def get_time():
    return {'time': time.time()}

@api.route('/login', methods=['POST'])
def login():
    print('HELLO')
    print(request.data)
    return request.data
