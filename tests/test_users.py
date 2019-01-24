from icc import db
from icc.models import Right, User
from tests.utils import get_token


def test_register(client):
    """Test user registration"""
    url = '/user/register'
    rv = client.get(url)
    assert rv.status_code == 200                    # page loads
    rv = client.post(
        url,
        data={'displayname': 'tester', 'email': 'george@test.com',
              'password': 'test', 'password2': 'test',
              'csrf_token': get_token(rv.data)},
        follow_redirects=True
    )
    assert rv.status_code == 200                    # page loads
    rv = client.get('user/list')
    assert b'tester' in rv.data                     # successful registration


def test_locked_login(popclient):
    "Test login of locked accounts."
    url = '/user/login'
    rv = popclient.get(url)
    assert rv.status_code == 200                    # page working
    rv = popclient.post(
        url,
        data={'email': 'community@example.com', 'password': 'testing',
              'csrf_token': get_token(rv.data)},
        follow_redirects=True
    )
    assert rv.status_code == 200                    # page working
    assert b'That account is locked' in rv.data     # account locked


def test_invalid_credentials_login(popclient):
    "Test login with invalid credentials."
    url = '/user/login'
    rv = popclient.get(url)
    assert rv.status_code == 200                    # page working
    rv = popclient.post(
        url,
        data={'email': 'george@example.com', 'password': 'nottesting',
              'csrf_token': get_token(rv.data)},
        follow_redirects=True
    )
    assert rv.status_code == 200                    # page working
    assert b'Invalid email or password' in rv.data  # login prevented


def test_login_logout(popclient):
    """Test login and logout."""
    url = '/user/login'
    rv = popclient.get(url)
    assert rv.status_code == 200                    # page working
    rv = popclient.post(
        url,
        data={'email': 'george@example.com', 'password': 'testing',
              'csrf_token': get_token(rv.data)},
        follow_redirects=True
    )
    assert rv.status_code == 200                    # page working
    assert b'logout' in rv.data                     # successful login
    assert b'login' not in rv.data                  # successful logout
    rv = popclient.get('/user/logout', follow_redirects=True)
    assert b'login' in rv.data                      # successful logout
    assert b'logout' not in rv.data                 # successful logout


def test_user_rep_authorized(app):
    """Test user authorized by reputation."""
    u = User(displayname='john', email='john@example.com', reputation=10)
    right = Right(enum='right_to_balloons', min_rep=10)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert u.is_authorized('right_to_balloons')     # user is authorized


def test_user_rep_not_authorized(app):
    """Test user not authorized by rep."""
    u = User(displayname='john', email='john@example.com', reputation=5)
    right = Right(enum='right_to_balloons', min_rep=10)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert not u.is_authorized('right_to_balloons')     # user is authorized


def test_user_rights_authorized(app):
    """Test user authorized by rights."""
    u = User(displayname='john', email='john@example.com', reputation=0)
    right = Right(enum='right_to_balloons', min_rep=None)
    u.rights = [right]
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert u.is_authorized('right_to_balloons')     # user is authorized


def test_user_rights_not_authorized(app):
    """Test user not authorized by rights."""
    u = User(displayname='john', email='john@example.com', reputation=0)
    right = Right(enum='right_to_balloons', min_rep=None)
    with app.app_context():
        db.session.add(right)
        db.session.commit()
        assert not u.is_authorized('right_to_balloons')  # user is not authorized


def test_password():
    """Test user password authentication."""
    u = User(displayname='john', email='john@example.com')
    u.set_password('dog')
    assert not u.check_password('cat')              # password is incorrect
    assert u.check_password('dog')                  # password is correct


def test_avatar():
    """Test user avatar url generation."""
    u = User(displayname='john', email='john@example.com')
    assert u.avatar(128) == 'https://www.gravatar.com/avatar/' \
                            'd4c74594d841139328695756648b6bd6?d=identicon&s=128'
