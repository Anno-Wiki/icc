from flask import url_for

from icc.models import Writer, Text, Tag


def test_writer_view(popclient):
    app, client = popclient

    with app.test_request_context():
        writers = Writer.query.all()
        for writer in writers:
            url = url_for('main.writer', writer_url=writer.url)
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(writer.name, 'utf-8') in rv.data


def test_text_view(popclient):
    app, client = popclient

    with app.test_request_context():
        texts = Text.query.all()
        for text in texts:
            url = url_for('main.text', text_url=text.url)
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(text.title, 'utf-8') in rv.data


def test_tag(popclient):
    app, client = popclient

    with app.test_request_context():
        tags = Tag.query.all()
        sorts = ['newest', 'oldest', 'weight', 'modified']
        for tag in tags:
            url = url_for('main.tag', tag=tag.tag)
            rv = client.get(url)
            assert rv.status_code == 200
            assert bytes(str(tag), 'utf-8') in rv.data
