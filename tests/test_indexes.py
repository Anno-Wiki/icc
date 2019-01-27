import math

from flask import url_for

from icc.models.content import  Writer, Text
from icc.models.annotation import Annotation, Tag
from icc.models.user import User


def test_writer_index(popclient):
    """Test the writer index page."""
    app, client = popclient

    sorts = ['youngest', 'oldest', 'last name', 'authored', 'edited',
             'translated', 'thisdoesntexist']
    with app.test_request_context():
        url = url_for("main.writer_index")
        entities = Writer.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    rv = client.get(url)
    assert rv.status_code == 200
    assert b'<div class="card">' in rv.data
    for sort in sorts:
        rv = client.get(f'{url}?sort={sort}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages+1}')
        assert rv.status_code == 404


def test_text_index(popclient):
    """Test the text index page."""
    app, client = popclient

    sorts = ['title', 'author', 'oldest', 'newest', 'length', 'annotations',
             'thisdoesntexist']
    with app.test_request_context():
        url = url_for('main.text_index')
        entities = Text.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    rv = client.get(url)
    assert rv.status_code == 200
    assert b'<div class="card">' in rv.data
    for sort in sorts:
        rv = client.get(f'{url}?sort={sort}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages+1}')
        assert rv.status_code == 404


def test_tag_index(popclient):
    """Test the tag index page."""
    app, client = popclient

    sorts = ['tag', 'annotations']
    with app.test_request_context():
        url = url_for('main.tag_index')
        entities = Tag.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    rv = client.get(f'{url}')
    assert rv.status_code == 200
    assert b'<tag>' in rv.data
    for sort in sorts:
        rv = client.get(f'{url}?sort={sort}')
        assert rv.status_code == 200
        assert b'<tag>' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages}')
        assert rv.status_code == 200
        assert b'<tag>' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages+1}')
        assert rv.status_code == 404


def test_user_index(minclient):
    """Test the user index page."""
    app, client = minclient

    sorts = ['reputation', 'name', 'annotation', 'edits']
    with app.test_request_context():
        url = url_for("user.index")
        entities = User.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    rv = client.get(f'{url}')
    assert rv.status_code == 200
    assert b'<div class="card">' in rv.data
    for sort in sorts:
        rv = client.get(f'{url}?sort={sort}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages}')
        assert rv.status_code == 200
        assert b'<div class="card">' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages+1}')
        assert rv.status_code == 404
