import inspect
import sys

from datetime import datetime

from sqlalchemy.orm import backref

from icc import db
from icc.models.mixins import Base, VoteMixin, FollowableMixin


class TextRequestVote(Base, VoteMixin):
    text_request_id = db.Column(
        db.Integer, db.ForeignKey('textrequest.id', ondelete='CASCADE'),
        index=True)
    text_request = db.relationship(
        'TextRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.text_request}"


class TextRequest(Base, FollowableMixin):
    title = db.Column(db.String(127), index=True)
    authors = db.Column(db.String(127), index=True)
    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    wikipedia = db.Column(db.String(127), default=None)
    gutenberg = db.Column(db.String(127), default=None)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id'), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    requester = db.relationship('User', backref='text_requests')
    text = db.relationship('Text', backref='request')

    def __repr__(self):
        return f'<Request for {self.title}>'

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def upvote(self, voter):
        weight = 1
        self.weight += weight
        vote = TextRequestVote(voter=voter, text_request=self, delta=weight)
        db.session.add(vote)

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TextRequestVote(voter=voter, text_request=self, delta=weight)
        db.session.add(vote)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f'{round(self.weight/1000000,1)}m'
        elif self.weight >= 1000 or self.weight <= -1000:
            return f'{round(self.weight/1000,1)}k'
        else:
            return f'{self.weight}'

    def reject(self):
        self.rejected = True


class TagRequestVote(Base, VoteMixin):
    tag_request_id = db.Column(
        db.Integer, db.ForeignKey('tagrequest.id', ondelete='CASCADE'),
        index=True)
    tag_request = db.relationship(
        'TagRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.tag_request}"


class TagRequest(Base, FollowableMixin):
    tag = db.Column(db.String(127), index=True)
    weight = db.Column(db.Integer, default=0, index=True)
    approved = db.Column(db.Boolean, default=False, index=True)
    rejected = db.Column(db.Boolean, default=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), index=True)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    wikipedia = db.Column(db.String(127), default=None)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    requester = db.relationship('User', backref='tag_requests')
    created_tag = db.relationship('Tag', backref='tag_request')

    def rollback(self, vote):
        self.weight -= vote.delta
        db.session.delete(vote)

    def upvote(self, voter):
        weight = 1
        self.weight += weight
        vote = TagRequestVote(voter=voter, tag_request=self, delta=weight)
        db.session.add(vote)

    def downvote(self, voter):
        weight = -1
        self.weight += weight
        vote = TagRequestVote(voter=voter, tag_request=self, delta=weight)
        db.session.add(vote)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f'{round(self.weight/1000000,1)}m'
        elif self.weight >= 1000 or self.weight <= -1000:
            return f'{round(self.weight/1000,1)}k'
        else:
            return f'{self.weight}'


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
