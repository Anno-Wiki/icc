import os
import yaml
import pytest

from icc import create_app, db
from icc import classes

from config import Config


DIR = os.path.dirname(os.path.realpath(__file__))
PASSWORD = 'testing'


class TestConfig(Config):
    """The test config object for building the app."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    ELASTICSEARCH_URL = None


@pytest.fixture
def app():
    """Create the app; this is the fundamental fixture. The mother fixture..."""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def appclient(app):
    """Return an unpopulated test client."""
    return app, app.test_client()


@pytest.fixture
def minpop(app):
    """Populate the database with minimal dummy data, return the app."""
    fin = open(f'{DIR}/enums.yml', 'rt')
    data = yaml.load(fin)

    with app.app_context():
        # populate remaining enums
        for enum, enums in data.items():
            for instance in enums:
                obj = classes[enum](**instance)
                if enum == 'User':
                    obj.set_password(PASSWORD)
                db.session.add(obj)

        db.session.commit()

    return app


@pytest.fixture
def minclient(minpop):
    """Return the minimally populated app and it's test client."""
    return minpop, minpop.test_client()


@pytest.fixture
def pop(minpop):
    """Populate the database with the rest of the dummy data, return the app."""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    fin = open(f'{DIR}/data.yml', 'rt')
    data = yaml.load(fin)

    with minpop.app_context():
        # populate remaining enums
        for enum, enums in data['enums'].items():
            for instance in enums:
                obj = classes[enum](**instance)
                db.session.add(obj)

        # pop authors and edition from text
        authors = data['text'].pop('authors')
        edition = data['text'].pop('edition')

        # populate the text
        t = classes['Text'](**data['text'])
        db.session.add(t)

        # populate the authors
        for author in authors:
            t.authors.append(classes['Writer'](**author))

        # pop annotations and lines from edition
        annotations = edition.pop('annotations')
        lines = edition.pop('lines')

        # populate the edition
        e = classes['Edition'](text=t, **edition)
        db.session.add(e)

        # popoulate the lines
        labels = classes['LineEnum'].query.all()
        label = {}
        for l in labels:
            label[f'{l.enum}>{l.display}'] = l
        for line in lines:
            db.session.add(
                classes['Line'](
                    edition=e, num=line['num'], label=label[line['enum']],
                    em_status=label[line['em_status']], lvl1=line['l1'],
                    lvl2=line['l2'], lvl3=line['l3'], lvl4=line['l4'],
                    line=line['line']
                )
            )

        # populate the annotations
        for a in annotations:
            annotator = a.pop('annotator')
            annotator = classes['User'].query.filter_by(
                displayname=annotator).first()
            tag_strings = a.pop('tags')
            tags = [classes['Tag'].query.filter_by(tag=tag).first() for tag in
                    tag_strings]
            db.session.add(
                classes['Annotation'](
                    annotator=annotator, edition=e, tags=tags, **a))
        db.session.commit()
    return minpop


@pytest.fixture
def popclient(pop):
    """Return the populated client."""
    return pop, pop.test_client()
