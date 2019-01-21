import pytest

from icc import create_app, db
from icc.models import classes, Text, Writer, Edition, LineEnum, Annotation,\
        User
from config import Config #dir_path = os.path.dirname(os.path.realpath(__file__))
#fin = open(f'{dir_path}/data.yml', 'rt')
#data = yaml.load(fin)
#authors = data['text'].pop('authors')
#edition = data['text'].pop('edition')
#annotations = edition.pop('annotations')
#lines = edition.pop('lines')
#text = data.pop('text')
#enums = data.pop('enums')
#password = 'testing'
#
class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    ELASTICSEARCH_URL = None
    #SERVER_NAME = 'www.testing.com'
    WTF_CSRF_ENABLED = 0

@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        db.session.add(User(displayname='test', email='test@test.com'))
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='session')
def client(app):
    return app.test_client()
