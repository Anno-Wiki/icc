"""Test admin.annotations routes."""

import math
from flask import url_for

from icc import db
from icc.models.annotation import Annotation
from icc.models.user import User

from tests.utils import login, TESTADMIN, TESTUSER2, looptest


def test_edit_review_queue(popclient):
    """Test the edit review queue."""
    app, client = popclient

    with app.test_request_context():
        annotations = Annotation.query.all()
        user = User.query.filter_by(email=TESTUSER2).first()

        entities = 0
        for annotation in annotations:
            annotation.edit(editor=user, reason="Just 'cause",
                            fl=annotation.HEAD.first_line_num,
                            ll=annotation.HEAD.last_line_num,
                            fc=annotation.HEAD.first_char_idx,
                            lc=annotation.HEAD.last_char_idx,
                            body=f'{annotation.HEAD.body} is stupid.',
                            tags=annotation.HEAD.tags)
            entities += 1
        db.session.commit()

        user = User.query.filter_by(email=TESTADMIN).first()
        login(user, client)
        url = url_for('admin.edit_review_queue')

    osorts = ['voted', 'id', 'edit_num', 'editor', 'time', 'reason']
    sorts = []
    for sort in osorts:
        sorts.append(sort)
        sorts.append(f'{sort}_invert')

    max_pages = int(math.ceil(entities/app.config['NOTIFICATIONS_PER_PAGE']))
    sorts = ['added', 'weight']

    test = 'cleared'
    looptest(client=client, url=url, max_pages=max_pages, sorts=sorts,
             test=test)
