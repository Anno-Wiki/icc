"""Test main.editions routes."""
import math
from flask import url_for
from icc.models.content import Edition


def test_edition(popclient):
    """Test the edition view page."""
    app, client = popclient

    with app.test_request_context():
        editions = Edition.query.all()
        for edition in editions:
            url = edition.url
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(edition.text.title, 'utf-8') in rv.data
            assert b'<tr class="lvl' in rv.data


def test_edition_annotations(popclient):
    """Test the annotations by edition page."""
    app, client = popclient

    with app.test_request_context():
        editions = Edition.query.all()

        assert len(editions) > 0

        sorts = ['newest', 'oldest', 'weight', 'line']
        for edition in editions:
            url = url_for('main.edition_annotations',
                          text_url=edition.text.url_name,
                          edition_num=edition.num)
            entities = edition.annotations.count()
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
