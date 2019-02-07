import pytest

from flask import url_for
from tests.utils import get_token
from icc import db
from icc.models.user import User


def test_before_request_lockout(minclient):
    """Test the lockout functionality on the before_request route.

    I am purposely going to access a page other than those in the main.routes
    module to test that it works gloally.

    This test is marked xfail for now. I have to determine how to globally set
    the before_request route. I am worried I cannot and will have to implement
    it in each of my blueprints.

    """
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

    with app.test_request_context():
        user = User.query.filter_by(email='george@example.com').first()
        user.locked = True
        db.session.commit()
        url = url_for('user.profile')
        rv = client.get(url)
        assert rv.status_code == 200
        assert b'login' in rv.data
