import os
import yaml
import pytest

from icc import create_app, db
from icc.models import classes

from config import Config


# a testing version of Config that overrides some vars
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

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Return an unpopulated test client."""
    return app.test_client()


@pytest.fixture
def pop(app):
    """Populate the database with dummy data, return the app."""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    fin = open(f'{dir_path}/data.yml', 'rt')
    data = yaml.load(fin)

    password = 'testing'
    # populate all enums
    for enum, enums in data['enums'].items():
        for instance in enums:
            obj = classes[enum](**instance)
            if enum == 'User':
                obj.set_password(password)
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
    return app


@pytest.fixture
def popclient(pop):
    """Return the populated client."""
    return pop.test_client()
