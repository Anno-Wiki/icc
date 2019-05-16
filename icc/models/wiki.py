"""Wiki models."""
import sys
import inspect

from flask import flash, url_for, current_app as app

from sqlalchemy import orm
from sqlalchemy.orm import backref

from icc.models.mixins import Base, EditMixin, VoteMixin, VotableMixin
from icc import db


class Wiki(Base):
    """An actual wiki. It has some idiosyncracies I'm not fond of, notably in
    init_on_load. But it's modelled after my Annotation system.
    """
    entity_string = db.Column(db.String(191), index=True)

    current = db.relationship(
        'WikiEdit', primaryjoin='and_(WikiEdit.entity_id==Wiki.id,'
        'WikiEdit.current==True)', uselist=False, lazy='joined')
    edits = db.relationship(
        'WikiEdit', primaryjoin='WikiEdit.entity_id==Wiki.id', lazy='dynamic')
    edit_pending = db.relationship(
        'WikiEdit', primaryjoin='and_(WikiEdit.entity_id==Wiki.id,'
        'WikiEdit.approved==False, WikiEdit.rejected==False)',
        passive_deletes=False)

    @orm.reconstructor
    def __init_on_load__(self):
        """The primary purpose of this method is to load the entity reference.
        """
        # This is a hack and needs to be improved.
        # Basically, we rely on the backref defined on the entity in order to
        # get the entity. I really want to make this more explicit and less
        # hacky.
        self.entity = list(
            filter(None, [self.writer, self.text, self.tag, self.edition,
                          self.textrequest, self.tagrequest]))[0]

    def __init__(self, *args, **kwargs):
        """Creating a new wiki also populates the first edit."""
        body = kwargs.pop('body', None)
        body = 'This wiki is currently blank.' if not body else body
        super().__init__(*args, **kwargs)
        self.versions.append(
            WikiEdit(current=True, body=body, approved=True,
                     reason='Initial Version.'))

    def __repr__(self):
        return f'<Wiki HEAD {str(self.entity)} at version {self.current.num}>'

    def edit(self, editor, body, reason):
        """Edit the wiki, creatinga new WikiEdit."""
        edit = WikiEdit(wiki=self, num=self.current.num+1, editor=editor,
                        body=body, reason=reason)
        db.session.add(edit)
        if editor.is_authorized('immediate_wiki_edits'):
            edit.approved = True
            self.current.current = False
            edit.current = True
            flash("The edit has been applied.")
        else:
            flash("The edit has been submitted for peer review.")


class WikiEditVote(Base, VoteMixin):
    """A Wiki Edit Vote."""
    edit_id = db.Column(db.Integer,
                        db.ForeignKey('wikiedit.id', ondelete='CASCADE'),
                        index=True, nullable=False)
    entity = db.relationship('WikiEdit', backref=backref('ballots',
                                                         passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.edit}"


class WikiEdit(Base, EditMixin, VotableMixin):
    """A WikiEdit."""
    __vote__ = WikiEditVote
    __reputable__ = 'editor'
    __approvable__ = 'immediate_wiki_edits'
    __margin_approvable__ = 'VOTES_FOR_APPROVAL'
    __margin_rejectable__ = 'VOTES_FOR_REJECTION'

    entity_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    wiki = db.relationship('Wiki', backref=backref('versions', lazy='dynamic'))

    def __repr__(self):
        return f"<WikiEdit on {self.wiki}>"

    @property
    def url(self):
        return url_for('admin.review_wiki_edit', wiki_id=self.wiki.id,
                       edit_id=self.id)


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
