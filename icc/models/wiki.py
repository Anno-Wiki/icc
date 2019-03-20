import sys
import inspect

from flask import flash, current_app as app

from sqlalchemy import orm
from sqlalchemy.orm import backref

from icc.models.mixins import Base, EditMixin, VoteMixin
from icc import db


class Wiki(Base):
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
    def init_on_load(self):
        # This is a hack and needs to be improved.
        # Basically, we rely on the backref defined on the entity in order to
        # get the entity. I really want to make this more explicit and less
        # hacky.
        self.entity = list(
            filter(None, [self.writer, self.text, self.tag, self.edition,
                          self.textrequest, self.tagrequest]))[0]

    def __init__(self, *args, **kwargs):
        body = kwargs.pop('body', None)
        body = 'This wiki is currently blank.' if not body else body
        super().__init__(*args, **kwargs)
        self.versions.append(
            WikiEdit(current=True, body=body, approved=True,
                     reason='Initial Version.'))

    def __repr__(self):
        return f'<Wiki HEAD {str(self.entity)} at version {self.current.num}>'

    def edit(self, editor, body, reason):
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
    edit_id = db.Column(db.Integer,
                        db.ForeignKey('wikiedit.id', ondelete='CASCADE'),
                        index=True, nullable=False)
    entity = db.relationship('WikiEdit', backref=backref('ballots',
                                                         passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.edit}"


class WikiEdit(Base, EditMixin):
    __vote__ = WikiEditVote
    entity_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)

    wiki = db.relationship('Wiki', backref=backref('versions', lazy='dynamic'))

    def __repr__(self):
        return f"<WikiEdit on {self.wiki}>"

    def upvote(self, voter):
        if self.approved or self.rejected:
            flash("That edit is no longer pending.")
            return
        if self.editor == voter:
            flash("You cannot vote on your own edits.")
            return
        ov = voter.get_vote(self)
        if ov:
            if ov.is_up():
                self.rollback(ov)
                return
            else:
                self.rollback(ov)
        vote = self.__vote__(entity=self, delta=1, voter=voter)
        self.weight += vote.delta
        db.session.add(vote)
        if self.weight >= app.config['VOTES_FOR_WIKI_EDIT_APPROVAL'] or\
                voter.is_authorized('immediate_wiki_edits'):
            self.approve()

    def downvote(self, voter):
        if self.approved or self.rejected:
            flash("That edit is no longer pending.")
            return
        if self.editor == voter:
            flash("You cannot vote on your own edits.")
            return
        ov = voter.get_vote(self)
        if ov:
            if not ov.is_up():
                self.rollback(ov)
                return
            else:
                self.rollback(ov)
        vote = self.__vote__(entity=self, delta=-1, voter=voter)
        self.weight += vote.delta
        db.session.add(vote)
        if self.weight <= app.config['VOTES_FOR_WIKI_EDIT_REJECTION'] or\
                voter.is_authorized('immediate_wiki_edits'):
            self.reject()

    def approve(self):
        self.approved = True
        self.wiki.current.current = False
        self.current = True
        flash("The edit was approved.")


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
