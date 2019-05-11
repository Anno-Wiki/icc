import inspect
import sys

from datetime import datetime

from flask import url_for
from sqlalchemy.orm import backref

from icc import db
from icc.models.mixins import Base, VoteMixin, FollowableMixin, VotableMixin
from icc.models.wiki import Wiki


class TextRequestVote(Base, VoteMixin):
    text_request_id = db.Column(
        db.Integer, db.ForeignKey('textrequest.id', ondelete='CASCADE'),
        index=True)
    entity = db.relationship(
        'TextRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.text_request}"


class TextRequest(Base, FollowableMixin, VotableMixin):
    __vote__ = TextRequestVote
    __reputable__ = 'requester'
    __approvable__ = 'approve_text_requests'
    __margin_approvable__ = 'VOTES_FOR_REQUEST_APPROVAL'
    __margin_rejectable__ = 'VOTES_FOR_REQUEST_REJECTION'

    title = db.Column(db.String(127), index=True)
    authors = db.Column(db.String(127), index=True)

    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    wiki = db.relationship('Wiki', backref=backref('textrequest',
                                                   uselist=False))

    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    requester = db.relationship('User', backref='text_requests')

    @property
    def url(self):
        return url_for('requests.view_text_request', request_id=self.id)

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = "This wiki is blank." if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Request for {self.title}>'


class TagRequestVote(Base, VoteMixin):
    tag_request_id = db.Column(
        db.Integer, db.ForeignKey('tagrequest.id', ondelete='CASCADE'),
        index=True)
    entity = db.relationship(
        'TagRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.tag_request}"


class TagRequest(Base, FollowableMixin, VotableMixin):
    __vote__ = TagRequestVote
    __reputable__ = 'requester'
    __approvable__ = 'approve_tag_requests'
    __margin_approvable__ = 'VOTES_FOR_REQUEST_APPROVAL'
    __margin_rejectable__ = 'VOTES_FOR_REQUEST_REJECTION'

    tag = db.Column(db.String(127), index=True)

    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    wiki = db.relationship('Wiki', backref=backref('tagrequest', uselist=False))

    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    requester = db.relationship('User', backref='tag_requests')

    @property
    def url(self):
        return url_for('requests.view_tag_request', request_id=self.id)

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = "This wiki is blank." if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Request for {self.tag}>'


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
