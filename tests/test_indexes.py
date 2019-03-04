import math
from flask import url_for
from icc.models.user import User
from tests.utils import looptest

def test_user_index(minclient):
    """Test the user index page."""
    app, client = minclient

    with app.test_request_context():
        url = url_for("user.index")
        entities = User.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

    sorts = ['reputation', 'name', 'annotation', 'edits']
    tests = ['<div class="card">']
    looptest(url=url, sorts=sorts, max_pages=max_pages, tests=tests,
             client=client)
