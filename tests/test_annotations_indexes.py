import math

from flask import url_for

from icc.models import Writer, Text, Annotation


def test_empty_db(appclient):
    """Start with a blank database."""
    client = appclient[1]
    rv = client.get('/')
    assert b'<annotation' not in rv.data            # database is empty


def test_index(popclient):
    """Test the main index page."""
    app, client = popclient

    sorts = ['newest', 'oldest', 'modified', 'weight', 'thisdoesntexist']
    with app.test_request_context():
        url = url_for('main.index')
        entities = Annotation.query.count()
        max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))

    rv = client.get(url)
    assert rv.status_code == 200
    assert b'<annotation' in rv.data
    for sort in sorts:
        rv = client.get(f'{url}?sort={sort}')
        assert rv.status_code == 200                                # sort
        assert b'<annotation' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages}')      # sort/page
        assert rv.status_code == 200
        assert b'<annotation' in rv.data
        rv = client.get(f'{url}?sort={sort}&page={max_pages+1}')    # max page
        assert rv.status_code == 404


def test_writer_annotations(popclient):
    """Test the annotations by writer page."""
    app, client = popclient

    with app.test_request_context():
        writers = Writer.query.all()

        assert len(writers) > 0

        sorts = ['newest', 'oldest', 'weight']
        for writer in writers:
            url = url_for('main.writer_annotations', writer_url=writer.url)
            entities = writer.annotations.count()
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


def test_text_annotations(popclient):
    """Test the annotations by text page."""
    app, client = popclient

    with app.test_request_context():
        texts = Text.query.all()

        assert len(texts) > 0

        sorts = ['newest', 'oldest', 'weight', 'line']
        for text in texts:
            url = url_for('main.text_annotations', text_url=text.url)
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
