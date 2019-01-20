import pytest

from icc import create_app, db
from config import Config

class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True
    ELASTICSEARCH_URL = None


@pytest.fixture
def client():

    app = create_app(TestConfig)

    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client
