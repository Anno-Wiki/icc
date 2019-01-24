def test_empty_db(client):
    """Start with a blank database."""
    rv = client.get('/')
    assert b'<annotation' not in rv.data            # database is empty


def test_index(popclient):
    rv = popclient.get('/')
    assert b'<annotation ' in rv.data               # database is not empty
