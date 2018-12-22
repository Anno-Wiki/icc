import os, unittest, yaml, argparse, copy, math
from flask import url_for, request
from app import app, db
from app.models import *
from app.forms import *

dir_path = os.path.dirname(os.path.realpath(__file__))

fin = open(f'{dir_path}/data_for_tests.yml', 'rt')
data = yaml.load(fin)

class MyTest(unittest.TestCase):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['ELASTICSEARCH_URL'] = None
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'www.annopedia.org'

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

            labels = LineEnum.query.all()
            label = {}
            for l in labels:
                label[f'{l.label}>{l.display}'] = l

            i = 1
            for line in lines:
                db.session.add(Line(edition=e, num=line['num'],
                    label=label[line['label']],
                    em_status=label[line['em_status']], lvl1=line['l1'],
                    lvl2=line['l2'], lvl3=line['l3'], lvl4=line['l4'],
                    line=line['line']))

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


    def test_user_funcs(self):
        u = User(displayname='john', email='john@example.com')
        u.set_password('dog')
        self.assertFalse(u.check_password('cat'))
        self.assertTrue(u.check_password('dog'))
        self.assertEqual(u.avatar(128), 
                ('https://www.gravatar.com/avatar/d4c74594d841139328695756648b6'
                'bd6?d=identicon&s=128'))


    def test_index(self):
        sorts = ['newest', 'oldest', 'modified', 'weight', 'thisdoesntexist']
        with app.app_context():
            url = url_for("index")
        entities = Annotation.query.count()
        max_pages = int(math.ceil(entities / app.config['ANNOTATIONS_PER_PAGE']))

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        for sort in sorts:
            result = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(result.status_code, 404)


    def test_writer_index(self):
        sorts = ['youngest', 'oldest', 'last name', 'authored', 'edited',
                'translated', 'thisdoesntexist']
        with app.app_context():
            url = url_for("writer_index")

        entities = Writer.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        for sort in sorts:
            result = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(result.status_code, 404)


    def test_text_index(self):
        sorts = ['title', 'author', 'oldest', 'newest', 'length', 'annotations',
                'thisdoesntexist']
        with app.app_context():
            url = url_for("text_index")

        entities = Text.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        for sort in sorts:
            result = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(result.status_code, 404)


    def test_tag_index(self):
        sorts = ['tag', 'index']
        with app.app_context():
            url = url_for("tag_index")

        entities = Tag.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        for sort in sorts:
            result = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(result.status_code, 404)


    def test_user_index(self):
        sorts = ['reputation', 'name', 'annotation', 'edits']
        with app.app_context():
            url = url_for("user.index")

        entities = User.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        for sort in sorts:
            result = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(result.status_code, 200)
            result = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(result.status_code, 404)


    def test_read(self):
        text = Text.query.first()

        line = Line.query.first()
        with app.app_context():
            url = line.get_url()

        result = self.app.get(f'{url}')
        self.assertEqual(result.status_code, 200)
        result = self.app.get(f'{url}&tag=definition')
        self.assertEqual(result.status_code, 200)

        with app.app_context():
            url = url_for('read', text_url=text.url)
        result = self.app.get(url)
        self.assertEqual(result.status_code, 200)
        result = self.app.get(f'{url}?tag=definition')
        self.assertEqual(result.status_code, 200)


if __name__ == '__main__':
    unittest.main()
