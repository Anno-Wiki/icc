import os, unittest, yaml, argparse, copy, math
from flask import url_for, request, g
from flask_login import current_user
from app import app, db
from app.models import *

dir_path = os.path.dirname(os.path.realpath(__file__))

    def test_secondaries_context(self):
        text = Text.query.first()
        self.assertNotEqual(text.annotations.count(), 0) # before app context
        with app.app_context():
            pass
        self.assertNotEqual(text.annotations.count(), 0) # after app context

    def test_secondaries_index(self):
        text = Text.query.first()
        self.assertNotEqual(text.annotations.count(), 0) # before app query
        rv = self.app.get('http://www.testing.com/index')
        self.assertEqual(rv.status_code, 200)
        self.assertNotEqual(text.annotations.count(), 0) # before app query


    def test_annotations(self):
        annotations = Annotation.query.all()
        for a in annotations:
            self.assertTrue(len(a.HEAD.tags) >= 1)
            self.assertTrue(len(a.HEAD.context) >= 1)
            self.assertTrue(len(a.HEAD.lines) >= 1)


    def test_index(self):
        sorts = ['newest', 'oldest', 'modified', 'weight', 'thisdoesntexist']
        with app.app_context():
            url = url_for("index")
        entities = Annotation.query.count()
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
        writer = Writer.query.first()

        self.assertTrue(writer.annotations.all())

        with app.app_context():
            url = url_for('writer_annotations', writer_url=writer.url)
        sorts = ['newest', 'oldest', 'weight']

        entities = writer.annotations.count()
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
        text = Text.query.first()
        with app.app_context():
            url = url_for('text_annotations', text_url=text.url)

        sorts = ['newest', 'oldest', 'weight', 'line']

        # this should return the number of annotations in the entire system but
        # it returns 0. We'll just hold off on this.
        #entities = text.annotations.count()
        entities = Annotation.query.count()
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
        tags = Tag.query.all()
        sorts = ['newest', 'oldest', 'weight', 'modified']
        for tag in tags:
            rv = self.app.get(f'https://www.example.com/tag/{tag.tag}')
            self.assertEqual(rv.status_code, 200)

            entities = tag.annotations.count()
            self.assertTrue(entities > 0)
            if entities == 1:
                max_pages = 1
            else:
                max_pages = int(math.ceil(entities/app.config['ANNOTATIONS_PER_PAGE']))
            for sort in sorts:
                rv = self.app.get(f'{url}?sort={sort}')
                self.assertEqual(rv.status_code, 200)
                rv = self.app.get(f'{url}?sort={sort}&page=1')
                self.assertEqual(rv.status_code, 200)
                rv = self.app.get(f'{url}?sort={sort}&page={max_pages+1}')
                if rv.status_code == 200:
                    print(rv.data)
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
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('annotation', annotation_id=annotation.id)
            self.assertEqual(self.app.get(url).status_code, 200)

    def test_edit_history(self):
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
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('view_edit', annotation_id=annotation.id, num=0)
            self.assertEqual(self.app.get(url).status_code, 200)


    def test_annotation_comments(self):
        for annotation in Annotation.query:
            with app.app_context():
                url = url_for('comments', annotation_id=annotation.id)
            self.assertEqual(self.app.get(url).status_code, 200)

    def test_annotate(self):
        db.session.commit()
        number_of_anotations = len(Annotation.query.all())
        with self.app:
            u = User.query.filter_by(displayname='malan').first()
            self.login(u.email, password)
            text = Text.query.first()
            edition = text.primary
            self.assertTrue(edition)
            chapters = Line.query.join(LineEnum,
                    Line.label_id==LineEnum.id).filter(LineEnum.label=='lvl1').all()
            for chapter in chapters:
                    data = { 'first_line': chapter.num+1,
                            'last_line': chapter.num+2,
                            'first_char_idx': 0, 'last_char_idx': -1,
                            'annotation': "This is a test!",
                            'reason': "Testing..."}
                    with app.app_context():
                        url = url_for('annotate', text_url=text.url,
                                edition_num=edition.num,
                                first_line=chapter.num+1,
                                last_line=chapter.num+2)
                    rv = self.app.post(url, data=data, follow_redirects=True)
                    self.assertEqual(rv.status_code, 200)
        self.assertEqual(Annotation.query.count(),
                Line.query.join(LineEnum, Line.label_id==LineEnum.id).filter(
                    LineEnum.label=='lvl1').count())
        with app.app_context():
            url = url_for("index")
        rv = self.app.get(url)
        self.assertTrue(b"This is a test" in rv.data)
        
    def test_secondaries(self):
        text = Text.query.first()
        self.assertTrue(text.annotations.count())


if __name__ == '__main__':
    unittest.main()
