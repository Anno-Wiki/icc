from icc.models import User

def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/')
    assert b'html' in rv.data

def test_user(app):
    """Test a test user."""
    with app.app_context():
        u = User.query.first()
    assert u.displayname == 'test'
    assert u.email == 'test@test.com'

def test_populated_db(popclient):
    """Test populating the database."""
    rv = popclient.get('/')
    assert rv.status_code == 200

