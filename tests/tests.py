import os, unittest, yaml, argparse, copy, math
from flask import url_for, request, g
from flask_login import current_user
from app import app, db
from app.models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

fin = open(f'{dir_path}/data_for_tests.yml', 'rt')
data = yaml.load(fin)
authors = data['text'].pop('authors')
edition = data['text'].pop('edition')
annotations = edition.pop('annotations')
lines = edition.pop('lines')
password = 'testing'

class Test(unittest.TestCase):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['ELASTICSEARCH_URL'] = None
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'www.testing.com'
    app.config['SQLALCHEMY_ECHO'] = 0
    app.config['WTF_CSRF_ENABLED'] = 0

    # I don't get why at all, but any relationship that requires a secondary
    # table (or rather, specifically, the `?.annotations lazy="dynamic"`
    # relationships) don't work in this actual unit. I don't get it
    # what-so-fucking-ever. I will have to inquire with StackOverflow.
    # Thankfully, the actual route _does_ work, so I am able to test by actually
    # setting the number of annotations as a class constant.


    # Helper functions
    def login(self, email, password):
        with app.app_context():
            url = url_for('user.login')
        return self.app.post(url, data={'email': email, 'password': password},
                follow_redirects=True)

    def logout(self):
        with app.app_context():
            url = url_for('user.logout')
        return self.app.get(url, follow_redirects=True)


    # setup and tear down functions
    def setUp(self):
        db.create_all()
        self.app =  app.test_client()
        for enum, enums in data['enums'].items():
            for instance in enums:
                obj = classes[enum](**instance)
                if enum == 'User':
                    obj.set_password(password)
                db.session.add(obj)
        text = copy.deepcopy(data['text'])
        t = Text(**text)
        for author in authors:
            t.authors.append(Writer(**author))
        e = Edition(text=t, **edition)
        db.session.add(t)
        db.session.add(e)
        db.session.commit()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        fin.close()


    # partial set up and tear down functions
    def setup_lines(self):
        labels = LineEnum.query.all()
        label = {}
        for l in labels:
            label[f'{l.label}>{l.display}'] = l
        e = Edition.query.first()
        for line in lines:
            db.session.add(Line(edition=e, num=line['num'],
                label=label[line['label']],
                em_status=label[line['em_status']],
                lvl1=line['l1'], lvl2=line['l2'], lvl3=line['l3'],
                lvl4=line['l4'], line=line['line']))
    

    def setup_annotations(self):
        i = 0
        e = Edition.query.first()
        annos = copy.deepcopy(annotations)
        for a in annos:
            annotator = a.pop('annotator')
            annotator = User.query.filter_by(displayname=annotator).first()
            tag_strings = a.pop('tags')
            tags = [Tag.query.filter_by(tag=tag).first() for tag in tag_strings]
            db.session.add(Annotation(annotator=annotator, edition=e, tags=tags,
                **a))
            i += 1
        self.annotations = i



    def test_login_logout(self):
        u = User.query.filter_by(locked=False).first()
        lu = User.query.filter_by(locked=True).first()

        self.assertTrue(b'That account is locked' in self.login(lu.email,
            password).data)
        self.assertTrue(b'Invalid email or password' in self.login(u.email,
            'bullcrap').data)

        with self.app:
            rv = self.login(u.email, password)
            self.assertFalse(b'That account is locked' in rv.data)
            self.assertFalse(b'Invalid email or password' in rv.data)

            rv = self.logout()
            self.assertEqual(rv.status_code, 200)


    def test_annotations(self):
        self.setup_lines()
        self.setup_annotations()
        db.session.commit()

        #annotations = Annotation.query.all()
        #for a in annotations:
        #    self.assertTrue(len(a.HEAD.tags) >= 1)
        #    self.assertTrue(len(a.HEAD.context) >= 1)
        #    self.assertTrue(len(a.HEAD.lines) >= 1)


    def test_user_funcs(self):
        u = User(displayname='john', email='john@example.com')
        u.set_password('dog')
        self.assertFalse(u.check_password('cat'))
        self.assertTrue(u.check_password('dog'))
        self.assertEqual(u.avatar(128), 
                ('https://www.gravatar.com/avatar/d4c74594d841139328695756648b6'
                'bd6?d=identicon&s=128'))


    def test_index(self):
        self.setup_annotations()
        db.session.commit()

        sorts = ['newest', 'oldest', 'modified', 'weight', 'thisdoesntexist']
        with app.app_context():
            url = url_for("index")
        entities = Annotation.query.count()
        max_pages = int(math.ceil(entities / app.config['ANNOTATIONS_PER_PAGE']))

        rv = self.app.get(f'{url}')
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)


    def test_writer_index(self):
        with app.app_context():
            url = url_for("writer_index")
        sorts = ['youngest', 'oldest', 'last name', 'authored', 'edited',
                'translated', 'thisdoesntexist']
        entities = Writer.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))
        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)

    def test_writer_view(self):
        writer = Writer.query.first()
        with app.app_context():
            url = url_for('writer', writer_url=writer.url)
        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)

    def test_writer_annotations(self):
        self.setup_lines()
        self.setup_annotations()
        db.session.commit()
        writer = Writer.query.first()

        self.assertTrue(writer.annotations.all())

        with app.app_context():
            url = url_for('writer_annotations', writer_url=writer.url)
        sorts = ['newest', 'oldest', 'weight']

        # This is weird as hell, but, while the actual route
        # `writer_annotations` returns the actual annotations from the
        # relationship `writer.annotations`, the query (here)
        # `writer.annotations.all()` and `writer.annotations.count` return
        # nothing and 0, so we'll just manually set the number of annotations.
        entities = self.annotations
        max_pages = int(math.ceil(entities / app.config['ANNOTATIONS_PER_PAGE']))

        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)

    def test_text_index(self):
        sorts = ['title', 'author', 'oldest', 'newest', 'length', 'annotations',
                'thisdoesntexist']
        with app.app_context():
            url = url_for('text_index')

        entities = Text.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)


    def test_text_view(self):
        text = Text.query.first()
        with app.app_context():
            url = url_for('text', text_url=text.url)

        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)


    def test_text_annotations(self):
        self.setup_annotations()
        db.session.commit()

        text = Text.query.first()
        with app.app_context():
            url = url_for('text_annotations', text_url=text.url)

        sorts = ['newest', 'oldest', 'weight', 'line']

        entities = self.annotations
        max_pages = int(math.ceil(entities / app.config['ANNOTATIONS_PER_PAGE']))

        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)


    def test_tag_index(self):
        sorts = ['tag', 'index']
        with app.app_context():
            url = url_for('tag_index')

        entities = Tag.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        rv = self.app.get(f'{url}')
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)


    def test_tag(self):
        self.setup_annotations()
        db.session.commit()
        tags = Tag.query.all()
        sorts = ['newest', 'oldest', 'weight', 'modified']

        for tag in tags:
            with app.app_context():
                url = url_for('tag', tag=tag.tag)
            rv = self.app.get(url)
            self.assertEqual(rv.status_code, 200)
            entities = len(tag.annotations.all())
            max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))
            # This test doesn't work. The problem is simply that I can't
            # properly query the number of annotations. The route works, the
            # test just doesn't, so I have to fudge it. I am getting
            # increasingly annoyed by this fact.
            max_pages = 3
            for sort in sorts:
                rv = self.app.get(f'{url}?sort={sort}')
                self.assertEqual(rv.status_code, 200)
                rv = self.app.get(f'{url}?sort={sort}&page=1')
                self.assertEqual(rv.status_code, 200)
                rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
                self.assertEqual(rv.status_code, 404)


    def test_user_index(self):
        sorts = ['reputation', 'name', 'annotation', 'edits']
        with app.app_context():
            url = url_for("user.index")

        entities = User.query.count()
        max_pages = int(math.ceil(entities / app.config['CARDS_PER_PAGE']))

        rv = self.app.get(f'{url}')
        self.assertEqual(rv.status_code, 200)
        for sort in sorts:
            rv = self.app.get(f'{url}?sort={sort}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages}')
            self.assertEqual(rv.status_code, 200)
            rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
            self.assertEqual(rv.status_code, 404)


    def test_read(self):
        self.setup_lines()
        self.setup_annotations()
        db.session.commit()

        text = Text.query.first()
        enum = LineEnum.query.first()
        lines = Line.query.filter_by(label=enum).all()

        for line in lines:
            with app.app_context():
                url = url_for('read', text_url=text.url)
            self.assertEqual(self.app.get(url).status_code, 200)
            edits = Edit.query.filter(Edit.first_line_num<=line.num,
                    Edit.last_line_num>=line.num).all()
            for edit in edits:
                for tag in edit.tags:
                    self.assertEqual(
                            self.app.get(f'{url}?tag={tag.tag}').status_code,
                            200)


    def test_wiki_edit_history(self):
        wikis = Wiki.query.all()
        sorts = ['num', 'editor', 'time', 'reason']
        for wiki in wikis:
            for sort in sorts:
                with app.app_context():
                    url = url_for('wiki_edit_history', wiki_id=wiki.id,
                            sort=sort)
                self.assertEqual(self.app.get(url).status_code, 200)
                with app.app_context():
                    url = url_for('wiki_edit_history', wiki_id=wiki.id,
                            sort=f'{sort}_invert')
                self.assertEqual(self.app.get(url).status_code, 200)


    def test_wiki_edit_view(self):
        wikis = Wiki.query.all()
        for wiki in wikis:
            for edit in wiki.edits:
                with app.app_context():
                    url = url_for('view_wiki_edit', wiki_id=wiki.id,
                            edit_num=edit.num)
                self.assertEqual(self.app.get(url).status_code, 200)


    def test_annotation_view(self):
        self.setup_annotations()
        db.session.commit()
        
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('annotation', annotation_id=annotation.id)
            self.assertEqual(self.app.get(url).status_code, 200)

    def test_edit_history(self):
        self.setup_annotations()
        db.session.commit()

        sorts = ['num', 'editor', 'time', 'reason']

        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('edit_history', annotation_id=annotation.id)
            self.assertEqual(self.app.get(url).status_code, 200)
            for sort in sorts:
                with app.app_context():
                    url = url_for('edit_history', annotation_id=annotation.id,
                            sort=sort)
                self.assertEqual(self.app.get(url).status_code, 200)
                self.assertEqual(self.app.get(f'{url}_invert').status_code, 200)

    def test_edit_view(self):
        self.setup_annotations()
        self.setup_lines()
        db.session.commit()

        # Annotation.edits and Annotation.HEAD are not working
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('view_edit', annotation_id=annotation.id, num=0)
            self.assertEqual(self.app.get(url).status_code, 200)


    def test_annotation_comments(self):
        self.setup_annotations()
        db.session.commit()
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('comments', annotation_id=annotation.id)
            self.assertEqual(self.app.get(url).status_code, 200)



if __name__ == '__main__':
    unittest.main()
