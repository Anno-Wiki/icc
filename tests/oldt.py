def test_annotations(self):
    annotations = Annotation.query.all()
    for a in annotations:
        self.assertTrue(len(a.HEAD.tags) >= 1)
        self.assertTrue(len(a.HEAD.context) >= 1)
        self.assertTrue(len(a.HEAD.lines) >= 1)


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
