"""Test admin.annotations routes."""

import math
from flask import url_for

from icc import db
from icc.models.annotation import Annotation, AnnotationFlag
from icc.models.user import User

from tests.utils import login, logout, TESTADMIN, TESTUSER, looptest


def test_deactivate(popclient):
    """Test the route to deactivate an annotation."""
    app, client = popclient

    with app.test_request_context():
        annotations = Annotation.query.all()
        user = User.query.filter_by(email=TESTADMIN).first()
        login(user, client)
        for annotation in annotations:
            url = url_for('admin.deactivate_annotation',
                          annotation_id=annotation.id)

            assert annotation.active
            rv = client.get(url, follow_redirects=True)
            assert rv.status_code == 200
            assert b'deactivated' in rv.data
            assert not annotation.active

            rv = client.get(url, follow_redirects=True)
            assert rv.status_code == 200
            assert b'reactivated' in rv.data
            assert annotation.active


def test_deactivated_list(popclient):
    """Test the route to deactivate an annotation."""
    app, client = popclient

    with app.test_request_context():
        annotations = Annotation.query.all()
        for annotation in annotations:
            annotation.active = False
        db.session.commit()

        user = User.query.filter_by(email=TESTADMIN).first()
        login(user, client)
        url = url_for('admin.view_deactivated_annotations')

    entities = len(annotations)
    max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))
    sorts = ['added', 'weight']

    test = '<annotation'
    looptest(sorts=sorts, url=url, max_pages=max_pages, client=client,
             test=test)


def test_all_annotation_flags(popclient):
    """Test the route to view all annotation flags for all annotations."""
    app, client = popclient

    with app.test_request_context():
        user = User.query.filter_by(email=TESTUSER).first()
        login(user, client)
        username = user.displayname

        flags = AnnotationFlag.enum_cls.query.all()
        annotations = Annotation.query.all()
        for annotation in annotations:
            for flag in flags:
                AnnotationFlag.flag(annotation, flag, user)
        db.session.commit()

        logout(client)
        user = User.query.filter_by(email=TESTADMIN).first()

        login(user, client)
        url = url_for('admin.all_annotation_flags')

        entities = AnnotationFlag.query.count()

    max_pages = int(math.ceil(entities/app.config['NOTIFICATIONS_PER_PAGE']))
    sorts = ['marked', 'marked_invert', 'flag', 'flag_invert', 'thrower',
             'thrower_invert', 'time', 'time_invert', 'resolver',
             'resolver_invert', 'time_resolved', 'time_resolved_invert',
             'annotation', 'annotation_invert', 'text', 'text_invert']


    looptest(test=username, sorts=sorts, max_pages=max_pages, url=url,
             client=client)


def test_annotation_flags(popclient):
    """Test the view page for annotation flags for a particular annotation."""
    app, client = popclient

    with app.test_request_context():
        annotation = Annotation.query.first()
        user = User.query.filter_by(email=TESTUSER).first()
        username = user.displayname

        login(user, client)
        flags = AnnotationFlag.enum_cls.query.all()
        for flag in flags:
            AnnotationFlag.flag(annotation, flag, user)
        db.session.commit()
        logout(client)

        user = User.query.filter_by(email=TESTADMIN).first()
        login(user, client)
        url = url_for('admin.annotation_flags', annotation_id=annotation.id)
        entities = AnnotationFlag.query.count()

    max_pages = int(math.ceil(entities/app.config['NOTIFICATIONS_PER_PAGE']))
    sorts = ['marked', 'marked_invert', 'flag', 'flag_invert', 'thrower',
             'thrower_invert', 'time', 'time_invert', 'resolver',
             'resolver_invert', 'time_resolved', 'time_resolved_invert']

    looptest(url=url, test=username, sorts=sorts, client=client,
             max_pages=max_pages)


def test_mark_annotation_flag(popclient):
    """Test the route to deactivate an annotation."""
    app, client = popclient

    with app.test_request_context():
        annotation = Annotation.query.first()
        user = User.query.filter_by(email=TESTADMIN).first()
        flags = AnnotationFlag.enum_cls.query.all()
        for flag in flags:
            AnnotationFlag.flag(annotation, flag, user)

        login(user, client)
        for flag in flags:
            url = url_for('admin.mark_annotation_flag', flag_id=flag.id)
            rv = client.get(url, follow_redirects=True)
            assert rv.status_code == 200
            assert b'marked resolved.' in rv.data

            rv = client.get(url, follow_redirects=True)
            assert rv.status_code == 200
            assert b'marked unresolved.' in rv.data


def test_mark_all_annotation_flags(popclient):
    """Test the route to mark all flags for a given annotation resolved."""
    app, client = popclient

    with app.test_request_context():
        annotation = Annotation.query.first()
        flags = AnnotationFlag.enum_cls.query.all()
        user = User.query.filter_by(email=TESTUSER).first()
        for flag in flags:
            AnnotationFlag.flag(annotation, flag, user)
        db.session.commit()

        user = User.query.filter_by(email=TESTADMIN).first()
        login(user, client)
        url = url_for('admin.mark_all_annotation_flags',
                      annotation_id=annotation.id)
        rv = client.get(url, follow_redirects=True)
        assert rv.status_code == 200
        assert b'All flags marked resolved.' in rv.data
