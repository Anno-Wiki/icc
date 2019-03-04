"""Test all of the main.text routes."""
import math
from flask import url_for
from icc.models.content import Text
from tests.utils import looptest


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

            test = '<annotation'
            looptest(test=test, url=url, sorts=sorts, client=client,
                     max_pages=max_pages)
