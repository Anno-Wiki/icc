import time

from flask import url_for
from icc import db
from icc.models.user import AdminRight, User
from tests.utils import get_token


def test_register(appclient):
    """Test user registration"""
    app, client = appclient
    with app.test_request_context():
        url = url_for('user.register')
    rv = client.get(url)
    assert rv.status_code == 200
    data={'displayname': 'tester', 'email': 'george@test.com',
          'password': 'test', 'password2': 'test',
          'csrf_token': get_token(rv.data)}
    rv = client.post(url, data=data, follow_redirects=True)
    assert rv.status_code == 200
    with app.test_request_context():
        url = url_for('user.index')
    rv = client.get(url)
    assert b'tester' in rv.data


def test_locked_login(minclient):
    """Test login of locked accounts."""
    app, client = minclient
    with app.test_request_context():
        url = url_for('user.login')
    rv = client.get(url)
    assert rv.status_code == 200
    data = {'email': 'community@example.com', 'password': 'testing',
            'csrf_token': get_token(rv.data)}
    rv = client.post(url, data=data, follow_redirects=True)
    assert rv.status_code == 200
    assert b'That account is locked' in rv.data


def test_invalid_credentials_login(minclient):
    """Test login with invalid credentials."""
    app, client = minclient
    with app.test_request_context():
        url = url_for('user.login')
    rv = client.get(url)
    assert rv.status_code == 200
    data = {'email': 'george@example.com', 'password': 'nottesting',
            'csrf_token': get_token(rv.data)}
    rv = client.post(url, data=data, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Invalid email or password' in rv.data


def test_login_logout(minclient):
    """Test login and logout."""
    app, client = minclient
    with app.test_request_context():
        url = url_for('user.login')
    rv = client.get(url)
    assert rv.status_code == 200
    data = {'email': 'george@example.com', 'password': 'testing',
            'csrf_token': get_token(rv.data)}
    rv = client.post(url, data=data, follow_redirects=True)
    assert rv.status_code == 200
    assert b'logout' in rv.data
    assert b'login' not in rv.data
    with app.test_request_context():
        url = url_for('user.logout')
    rv = client.get(url, follow_redirects=True)
    assert b'login' in rv.data
    assert b'logout' not in rv.data


def test_user_rep_authorized(app):
    """Test user authorized by reputation."""
    u = User(displayname='john', email='john@example.com', reputation=10)
    right = AdminRight(enum='right_to_balloons', min_rep=10)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert u.is_authorized('right_to_balloons')


def test_user_rep_not_authorized(app):
    """Test user not authorized by rep."""
    u = User(displayname='john', email='john@example.com', reputation=5)
    right = AdminRight(enum='right_to_balloons', min_rep=10)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert not u.is_authorized('right_to_balloons')


def test_user_rights_authorized(app):
    """Test user authorized by rights."""
    u = User(displayname='john', email='john@example.com', reputation=0)
    right = AdminRight(enum='right_to_balloons', min_rep=None)
    u.rights = [right]
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert u.is_authorized('right_to_balloons')


def test_user_rights_not_authorized(app):
    """Test user not authorized by rights."""
    u = User(displayname='john', email='john@example.com', reputation=0)
    right = AdminRight(enum='right_to_balloons', min_rep=None)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert not u.is_authorized('right_to_balloons')


def test_password():
    """Test user password authentication."""
    u = User(displayname='john', email='john@example.com')
    u.set_password('dog')
    assert not u.check_password('cat')
    assert u.check_password('dog')


def test_avatar():
    """Test user avatar url generation."""
    u = User(displayname='john', email='john@example.com')
    assert u.avatar(128) == 'https://www.gravatar.com/avatar/' \
                            'd4c74594d841139328695756648b6bd6?d=identicon&s=128'


def test_update_last_seen(app):
    """Test the update last time seen user function."""
    u = User(displayname='john', email='john@example.com')
    with app.app_context():
        db.session.add(u)
        db.session.commit()
        first = u.last_seen
        time.sleep(1)
        u.update_last_seen()
        assert first <= u.last_seen


def test_repr():
    """Test the user __repr__ function."""
    u = User(displayname='john', email='john@example.com')
    assert u != ''


def test_reset_password_token(app):
    """Test the reset password token validation system."""
    u = User(displayname='john', email='john@example.com')
    u.set_password('test')
    with app.app_context():
        db.session.add(u)
        db.session.commit()

        token = u.get_reset_password_token()
        assert token
        assert u == User.verify_reset_password_token(token)
        assert u != User.verify_reset_password_token('boogaloo')


def test_profile(minclient):
    """Test that the profile page url works."""
    app, client = minclient
    with app.test_request_context():
        u = User.query.get(2)
        url = url_for('user.login')
    rv = client.get(url)
    assert rv.status_code == 200
    data = {'email': u.email, 'password': 'testing',
            'csrf_token': get_token(rv.data)}
    client.post(url, data=data, follow_redirects=True)
    with app.test_request_context():
        url = url_for('user.profile', user_id=u.id)
    rv = client.get(url)
    assert bytes(u.displayname, 'utf-8') in rv.data
