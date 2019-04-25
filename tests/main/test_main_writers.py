"""Test the main.writers routes."""

import math
import pytest
from flask import url_for
from icc.models.content import Writer
from tests.utils import looptest


def test_writer_view(popclient):
    """Test the writer view page."""
    app, client = popclient

    with app.test_request_context():
        writers = Writer.query.all()
        for writer in writers:
            url = writer.url
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(writer.name, 'utf-8') in rv.data


def test_writer_annotations(popclient):
    """Test the annotations by writer page."""
    app, client = popclient

    with app.test_request_context():
        writers = Writer.query.all()
        assert len(writers) > 0
        sorts = ['newest', 'oldest', 'weight']
        for writer in writers:
            url = url_for('main.writer_annotations', writer_url=writer.url_name)
            entities = writer.annotations.count()
            assert entities > 0
            max_pages = int(math.ceil(
                    entities/app.config['ANNOTATIONS_PER_PAGE']))

            tests = ['class="annotation"']
            looptest(tests=tests, url=url, sorts=sorts, client=client,
                     max_pages=max_pages)


def test_writer_index(popclient):
    """Test the writer index page.
    """
    app, client = popclient

    sorts = ['last name', 'age', 'youth', 'authored', 'edited', 'translated',
             'thisdoesntexist']
    with app.test_request_context():
        url = url_for("main.writer_index")
        entities = Writer.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    tests = ['<div class="card">']
    looptest(tests=tests, url=url, max_pages=max_pages, client=client,
             sorts=sorts)
