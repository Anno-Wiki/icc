"""The main configuration file for pytest"""

import os
import io
import json
import yaml
import pytest

from icc import create_app, db
from icc import classes

from config import Config
from tests.utils import TESTADMIN, PASSWORD

from inserts.insertlines import (get_text, get_edition, populate_lines,
                                 add_writer_connections)


DIR = os.path.dirname(os.path.realpath(__file__))


class TestConfig(Config):
    """The test config object for building the app."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    ELASTICSEARCH_URL = None


def open_json(filename):
    """Helper function to return a json loaded file with the BOM eliminated from
    the data directory (just in case, because it seems to happen a lot that the
    BOM is in there and I fail to open the file).

    Parameters
    ----------
    filename : string
        The filename of the json file to be opened in the `tests/data`
        directory.
    """
    return json.load(open(f'{DIR}/data/{filename}', 'rt'))


@pytest.fixture
def app():
    """Create the app and yield it; this is the fundamental fixture. The mother
    fixture...
    """
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def appclient(app):
    """Return the app and an unpopulated test client in a tuple."""
    return app, app.test_client()


@pytest.fixture
def minpop(app):
    """Populate the database with minimal dummy data, return the app."""
    data = open_json(f'enums.json')

    with app.app_context():
        for enum, enums in data.items():
            for instance in enums:
                obj = classes[enum](**instance)
                if enum == 'User':
                    obj.set_password(PASSWORD)
                db.session.add(obj)

        # make the admin
        rights = classes['AdminRight'].query.all()
        u_cls = classes['User']
        u_cls.query.filter_by(email=TESTADMIN).first().rights = rights

        db.session.commit()
    return app


@pytest.fixture
def minclient(minpop):
    """Return the minimally populated app and it's test client in a tuple."""
    return minpop, minpop.test_client()


@pytest.fixture
def pop(minpop):
    """Populate the database with the rest of the dummy data, return the app."""

    enumdata = open_json('enums.text.json')
    lines = open_json('gravity.json')
    annotations = open_json('annotations.json')
    textconfig = yaml.load(open(f'{DIR}/data/gravity.config.yml', 'rt'),
                           Loader=yaml.FullLoader)

    with minpop.app_context():
        # populate remaining enums
        for enum, enums in enumdata.items():
            for instance in enums:
                obj = classes[enum](**instance)
                db.session.add(obj)

        # populate the text, edition, author, and lines
        text = get_text(textconfig, True)
        edition = get_edition(textconfig, text)
        add_writer_connections(textconfig, edition)
        populate_lines(lines, edition)

        # populate the annotations
        for a in annotations:
            annotator = a.pop('annotator')
            annotator = classes['User'].query\
                .filter_by(displayname=annotator).first()
            tag_strings = a.pop('tags')
            tags = [classes['Tag'].query.filter_by(tag=tag).first() for tag in
                    tag_strings]
            db.session.add(classes['Annotation'](annotator=annotator,
                                                 edition=edition, tags=tags,
                                                 **a))
        db.session.commit()
    return minpop


@pytest.fixture
def popclient(pop):
    """Return the populated app and a test client in a tuple."""
    return pop, pop.test_client()
