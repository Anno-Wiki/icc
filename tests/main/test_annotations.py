from flask import url_for

from icc.models.content import Text, Line
from icc.models.annotation import Annotation
from icc.models.user import User

from tests.utils import get_token


def test_annotate_page(popclient):
    """Test annotating."""
    app, client = popclient

    with app.test_request_context():
        u = User.query.filter_by(displayname='george').first()

        # logging in
        url = url_for('user.login')
        rv = client.get(url)
        data = {'email': u.email, 'password': 'testing',
                'csrf_token': get_token(rv.data)}
        rv = client.post(url, data=data, follow_redirects=True)
        assert rv.status_code == 200
        assert b'logout' in rv.data

        # getting the context
        text = Text.query.first()
        edition = text.primary
        line = Line.query.first()

        # annotating
        count = Annotation.query.count()
        url = url_for('main.annotate',
                      text_url=text.url, edition_num=edition.num,
                      first_line=line.num+1, last_line=line.num+2)
        rv = client.get(url)
        data = {'first_line': line.num+1, 'last_line': line.num+2,
                'first_char_idx': 0, 'last_char_idx': -1,
                'annotation': "This is a test!", 'reason': "Testing...",
                'csrf_token': get_token(rv.data)}
        rv = client.post(url, data=data, follow_redirects=True)
        assert rv.status_code == 200

        # checking the count
        newcount = Annotation.query.count()
        assert newcount == count + 1

        # testing that it posted
        url = url_for('main.index')
        rv = client.get(url)
        assert b"This is a test!" in rv.data


def test_edit_page(popclient):
    """Test editing annotations."""
    app, client = popclient

    with app.test_request_context():
        u = User.query.filter_by(displayname='george').first()

        # logging in
        url = url_for('user.login')
        rv = client.get(url)
        data = {'email': u.email, 'password': 'testing',
                'csrf_token': get_token(rv.data)}
        rv = client.post(url, data=data, follow_redirects=True)
        assert rv.status_code == 200
        assert b'logout' in rv.data

        # annotating
        annotation = Annotation.query.first()
        url = url_for('main.edit', annotation_id=annotation.id)
        rv = client.get(url, follow_redirects=True)
        assert rv.status_code == 200
        data = {'first_line': annotation.HEAD.first_line_num+1,
                'last_line': annotation.HEAD.first_line_num+1,
                'first_char_idx': 0, 'last_char_idx': -1,
                'annotation': "This is a test!", 'reason': "Testing...",
                'csrf_token': get_token(rv.data)}
        rv = client.post(url, data=data, follow_redirects=True)
        assert rv.status_code == 200

        # testing that it went through
        url = url_for('main.annotation', annotation_id=annotation.id)
        rv = client.get(url)
        assert rv.status_code == 200
        assert b"This is a test!" in rv.data


def test_annotations_page(popclient):
    """Test annotation view."""
    app, client = popclient

    with app.test_request_context():
        annotation = Annotation.query.first()
        url = url_for('main.annotation', annotation_id=annotation.id)
        rv = client.get(url)
        assert rv.status_code == 200
        assert bytes(f'[{annotation.id}]', 'utf-8') in rv.data


def test_annotations_object(popclient):
    """Test the annotations object."""
    app, client = popclient

    with app.app_context():
        annotations = Annotation.query.all()
        for a in annotations:
            assert a.HEAD.body
            assert a.HEAD.tags
            assert a.HEAD.context
