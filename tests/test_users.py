import re
from icc.models import classes


def get_token(data):
    m = re.search(b'<input id="csrf_token" name="csrf_token" type="hidden" value="(.*)">', data)
    return m.group(1).decode("utf-8")


def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/')
    assert b'html' in rv.data


def test_index(popclient):
    rv = popclient.get('/')
    assert b'<annotation ' in rv.data


def test_register(client):
    """Test user registration"""
    url = '/user/register'
    rv = client.get(url)
    assert rv.status_code == 200
    rv = client.post(url,
            data={
                'displayname': 'tester', 
                'email': 'george@test.com',
                'password': 'test',
                'password2': 'test',
                'csrf_token': get_token(rv.data)
                },
            follow_redirects=True)
    assert rv.status_code == 200
    rv = client.get('user/list')
    assert b'tester' in rv.data


def test_login_logout(popclient):
    """Test login and logout."""
    url = '/user/login'
    rv = popclient.get(url)
    assert rv.status_code == 200
    for l in rv.data.split(b'\n'):
        if b'csrf_token' in l:
            print(l)
    print(f"Get method: {get_token(rv.data)}")
    rv = popclient.post(url,
            data={
                'email': 'george@example.com',
                'password': 'testing',
                'csrf_token': get_token(rv.data)
                },
            follow_redirects=True)
    assert rv.status_code == 200
    assert b'logout' in rv.data
