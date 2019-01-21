from icc.models import User

#def test_empty_db(client):
#    """Start with a blank database."""
#
#    rv = client.get('/')
#    assert b'html' in rv.data

#def test_populated_db(client):
#    rv = client.get('/')
#    assert rv.status_code == 200

def test_user(app):
    with app.app_context():
        u = User.query.first()
    assert u.displayname == 'test'
    assert u.email == 'test@test.com'
