"""Test all of the main.routes routes."""
import pytest
import math

from flask import url_for
from tests.utils import login, TESTUSER, looptest
from icc import db
from icc.models.user import User
from icc.models.annotation import Annotation


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
        u = User.query.filter_by(email=TESTUSER).first()
        login(u, client)
        u.locked = True
        db.session.commit()
        url = u.url
        rv = client.get(url)
        assert rv.status_code == 200
        assert b'login' in rv.data


@pytest.mark.xfail
def test_search(popclient):
    """Test the search view.

    This is marked to fail for now. I turn off the elasticsearch engine when I'm
    testing because I don't want to repopulate it.

    I think, perhaps, there might be a way to create a test index, to be
    populated and dropped during the test.

    Will investigate. Simply marking fail for now.
    """
    app, client = popclient
    with app.test_request_context():
        url = url_for('main.search')
        rv = client.get(f'{url}?q=urine')
        assert rv.status_code == 200
        assert b'cascade of urine the rhino releases,' in rv.data


def test_index(popclient):
    """Test the main index page."""
    app, client = popclient

    sorts = ['newest', 'oldest', 'modified', 'weight', 'thisdoesntexist']
    with app.test_request_context():
        url = url_for('main.index')
        entities = Annotation.query.count()
        max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))


    tests = ['<annotation']
    looptest(url=url, max_pages=max_pages, tests=tests, client=client,
             sorts=sorts)


def test_line_annotations(popclient):
    """Test the annotations page for a given line."""
    app, client = popclient

    sorts = ['newest', 'oldest', 'weight', 'modified', 'thisdoesntexist']
    with app.test_request_context():
        url = url_for('main.line_annotations', text_url='Gravity', line_num=2)
        entities = 1
        max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))

    rv = client.get(url)
    assert rv.status_code == 200
    assert b'<annotation' in rv.data
    assert (b"Cygnus X-1 is a real black hole, but Cygnus, for the record, is "
            b"Latin for swan." in rv.data)

    tests = ['<annotation']
    looptest(url=url, max_pages=max_pages, tests=tests, client=client,
             sorts=sorts)


def test_read(popclient):
    """Test the read route.

    This test is simplistic for now. It should get more sophisticated in the
    future.
    """
    app, client = popclient

    with app.test_request_context():
        # naked route
        url = url_for('main.read', text_url='Gravity')
        rv = client.get(url)
        # First line of poem in data.
        assert b'Upon the black hole Cygnus X-1 that wobbles' in rv.data
        # Last line of poem *not* in data.
        assert b'gravity, if it could, would recuse itself.' not in rv.data
        # stanza 2
        url = url_for('main.read', text_url='Gravity', section=2)
        rv = client.get(url)
        # First line of second stanza in poem.
        assert b'In the wings of the Eskimo curlew' in rv.data
        # Last line of poem *not* in data.
        assert b'gravity, if it could, would recuse itself.' not in rv.data
