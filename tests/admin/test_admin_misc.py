from flask import url_for

from icc.models.content import Line
from icc.models.user import User

from tests.utils import get_token, login, TESTADMIN


def test_edit_page(popclient):
    """Test editing annotations."""
    app, client = popclient

    with app.test_request_context():
        user = User.query.filter_by(email=TESTADMIN).first()

        login(user, client)

        line = Line.query.first()
        testline = line.line + 'This is a test.'
        url = url_for('admin.edit_line', line_id=line.id)

        rv = client.get(url, follow_redirects=True)
        assert rv.status_code == 200
        data = {'line': testline, 'csrf_token': get_token(rv.data)}
        rv = client.post(url, data=data, follow_redirects=True)
        assert rv.status_code == 200
        assert bytes(testline, 'utf-8') in rv.data
