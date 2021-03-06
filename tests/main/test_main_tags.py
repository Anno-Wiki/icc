"""Test all of the main.tags routes."""
import math
from flask import url_for
from icc.models.annotation import Tag
from tests.utils import looptest

def test_tag_index(popclient):
    """Test the tag index page."""
    app, client = popclient

    sorts = ['tag', 'annotations']
    with app.test_request_context():
        url = url_for('main.tag_index')
        entities = Tag.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    tests = ['tag']
    looptest(url=url, client=client, sorts=sorts, tests=tests,
             max_pages=max_pages)


def test_tag(popclient):
    """Test the tag view page."""
    app, client = popclient

    with app.test_request_context():
        tags = Tag.query.all()
        for tag in tags:
            url = url_for('main.tag', tag=tag.tag)
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(f'<div class="tag', 'utf-8') in rv.data


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

            tests = ['class="annotation"']
            looptest(client=client, max_pages=max_pages, url=url, sorts=sorts,
                     tests=tests)
