"""Test all of the main.text routes."""
import math
from flask import url_for
from icc.models.content import Text


def test_text_view(popclient):
    """Test the text view page."""
    app, client = popclient

    with app.test_request_context():
        texts = Text.query.all()
        for text in texts:
            url = text.url
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(text.title, 'utf-8') in rv.data


def test_text_annotations(popclient):
    """Test the annotations by text page."""
    app, client = popclient

    with app.test_request_context():
        texts = Text.query.all()
        assert len(texts) > 0

        sorts = ['newest', 'oldest', 'weight', 'line']
        for text in texts:
            url = url_for('main.text_annotations', text_url=text.url_name)
            entities = text.annotations.count()
            assert entities > 0
            max_pages = int(math.ceil(
                    entities/app.config['ANNOTATIONS_PER_PAGE']))
            rv = client.get(url)
            assert rv.status_code == 200
            assert b'<annotation' in rv.data
            for sort in sorts:
                rv = client.get(f'{url}?sort={sort}')
                assert rv.status_code == 200
                assert b'<annotation' in rv.data
                rv = client.get(f'{url}?sort={sort}&page={max_pages}')
                assert rv.status_code == 200
                assert b'<annotation' in rv.data
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
