"""Test all of the main.tags routes."""
import math
from flask import url_for
from icc.models.annotation import Tag

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


def test_tag(popclient):
    """Test the tag view page."""
    app, client = popclient

    with app.test_request_context():
        tags = Tag.query.all()
        for tag in tags:
            url = url_for('main.tag', tag=tag.tag)
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(str(tag), 'utf-8') in rv.data


def test_tag_annotations(popclient):
    """Test the annotations by text page."""
    app, client = popclient

    with app.test_request_context():
        tags = Tag.query.all()
        assert len(tags) > 0

        sorts = ['newest', 'oldest', 'weight', 'line']
        for tag in tags:
            url = url_for('main.tag_annotations', tag=tag.tag)
            entities = tag.annotations.count()
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
