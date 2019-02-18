import re
from flask import url_for

def get_token(data):
    m = re.search(b'<input id="csrf_token" name="csrf_token" type="hidden" value="(.*)">', data)
    return m.group(1).decode("utf-8")

def login(user, client):
    url = url_for('user.login')
    rv = client.get(url)
    data = {'email': user.email, 'password': 'testing',
            'csrf_token': get_token(rv.data)}
    rv = client.post(url, data=data, follow_redirects=True)
    assert rv.status_code == 200
    assert b'logout' in rv.data
