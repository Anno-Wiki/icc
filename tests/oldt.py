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
