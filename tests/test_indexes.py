import math
from flask import url_for
from icc.models.user import User


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
