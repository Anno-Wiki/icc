import time
from icc.api import api

@api.route('/time')
def get_time():
    return {'time': time.time()}
