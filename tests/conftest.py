import pytest

import app
from app import db

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['ELASTICSEARCH_URL'] = None

    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client
