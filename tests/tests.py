import os, unittest, yaml, argparse, copy
from flask import url_for, request
from app import app, db
from app.models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

fin = open(f'{dir_path}/data_for_tests.yml', 'rt')
data = yaml.load(fin)

class MyTest(unittest.TestCase):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['ELASTICSEARCH_URL'] = None
    app.config['TESTING'] = True

    def setUp(self):
        db.create_all()
        self.app =  app.test_client()
        for enum, enums in data['enums'].items():
            for instance in enums:
                db.session.add(classes[enum](**instance))
        texts = copy.deepcopy(data['text'])
        for text in texts:
            authors = text.pop('authors')
            edition = text.pop('edition')
            t = Text(**text)
            for author in authors:
                t.authors.append(Writer(**author))
            lines = edition.pop('lines')
            annotations = edition.pop('annotations')
            e = Edition(text=t, **edition)
            db.session.add(t)
            db.session.add(e)
            for a in annotations:
                annotator = a.pop('annotator')
                annotator = User.query\
                        .filter_by(displayname=annotator).first()
                tag_strings = a.pop('tags')
                tags = [Tag.query.filter_by(tag=tag).first() for tag in
                        tag_strings]
                db.session.add(Annotation(annotator=annotator, edition=e,
                    tags=tags, **a))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        fin.close()

    def test_password_hashing(self):
        u = User.query.get(1)
        u.set_password('dog')
        self.assertFalse(u.check_password('cat'))
        self.assertTrue(u.check_password('dog'))

    def test_avatar(self):
        u = User(displayname='john', email='john@example.com')
        self.assertEqual(u.avatar(128), 
                ('https://www.gravatar.com/avatar/d4c74594d841139328695756648b6'
                'bd6?d=identicon&s=128'))

    def test_index(self):
        result = self.app.get('/index/')
        self.assertEqual(result.status_code, 200)

if __name__ == '__main__':
    unittest.main()
