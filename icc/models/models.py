import jwt
import inspect
import sys
import string

from time import time
from hashlib import sha1, md5
from math import log10
from datetime import datetime

from flask import url_for, abort, flash, current_app as app
from flask_login import UserMixin, current_user

from sqlalchemy import orm
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr

from icc.models.wiki import Wiki



from icc.models.mixins import Base, EnumMixin, VoteMixin, SearchableMixin, \
    EditMixin

from icc.models.tables import authors, tags, rights
from icc.models.tables import text_flrs, writer_flrs, user_flrs, tag_flrs, \
    annotation_flrs, text_request_flrs, tag_request_flrs

# Please note, if this last import is not the last import you can get some weird
# errors; please keep that as last.
from icc import db


class Writer(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    last_name = db.Column(db.String(128), index=True)
    birth_date = db.Column(db.Date, index=True)
    death_date = db.Column(db.Date, index=True)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    wiki = db.relationship('Wiki', backref=backref('writer', uselist=False))
    authored = db.relationship('Text', secondary=authors)
    edited = db.relationship(
        'Edition', secondary='join(WriterEditionConnection, ConnectionEnum)',
        primaryjoin='and_(WriterEditionConnection.writer_id==Writer.id,'
        'ConnectionEnum.enum=="editor")',
        secondaryjoin='Edition.id==WriterEditionConnection.edition_id',
        backref='editors')
    translated = db.relationship(
        'Edition', secondary='join(WriterEditionConnection, ConnectionEnum)',
        primaryjoin='and_(WriterEditionConnection.writer_id==Writer.id,'
        'ConnectionEnum.enum=="translator")',
        secondaryjoin='Edition.id==WriterEditionConnection.edition_id',
        backref='translators')
    annotations = db.relationship(
        'Annotation', secondary='join(text,authors).join(Edition)',
        primaryjoin='Writer.id==authors.c.writer_id',
        secondaryjoin='and_(Text.id==Edition.text_id,Edition.primary==True,'
        'Annotation.edition_id==Edition.id)', lazy='dynamic')

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = 'This writer does not have a biography yet.'\
            if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.name.replace(' ', '_')
        self.first_name = self.name.split(' ', 1)[0]

    def __repr__(self):
        return f'<Writer: {self.name}>'

    def __str__(self):
        return self.name

    def get_url(self):
        return url_for('main.writer', writer_url=self.url)


class Text(Base):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    sort_title = db.Column(db.String(128), index=True)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    published = db.Column(db.Date)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    wiki = db.relationship('Wiki', backref=backref('text', uselist=False))
    authors = db.relationship('Writer', secondary='authors')
    editions = db.relationship('Edition', lazy='dynamic')
    primary = db.relationship(
        'Edition',
        primaryjoin='and_(Edition.text_id==Text.id,Edition.primary==True)',
        uselist=False)

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.title.translate(
            str.maketrans(dict.fromkeys(string.punctuation))).replace(' ', '_')

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = "This wiki is blank." if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Text {self.id}: {self.title}>'

    def __str__(self):
        return self.title

    def get_url(self):
        return url_for('main.text', text_url=self.url)


class Edition(Base):
    id = db.Column(db.Integer, primary_key=True)
    num = db.Column(db.Integer, default=1)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id'))
    primary = db.Column(db.Boolean, default=False)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    published = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    wiki = db.relationship('Wiki', backref=backref('edition', uselist=False))
    text = db.relationship('Text')
    lines = db.relationship(
        'Line', primaryjoin='Line.edition_id==Edition.id', lazy='dynamic')

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = 'This wiki is blank.' if not description else description
        super().__init__(*args, **kwargs)
        self.title = f'{self.text.title} - Primary Edition*'\
            if self.primary else f'{self.text.title} - Edition #{self.num}'

        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def init_on_load(self):
        self.url = self.text.title.replace(' ', '_') + f'_{self.num}'
        self.title = f'{self.text.title} - Primary Edition*'\
            if self.primary else f'{self.text.title} - Edition #{self.num}'

    def __repr__(self):
        return f'<Edition #{self.num} {self.text.title}>'

    def __str__(self):
        return self.title

    def get_url(self):
        return url_for('main.edition', text_url=self.text.url,
                       edition_num=self.num)


class WriterEditionConnection(Base):
    id = db.Column(db.Integer, primary_key=True)
    writer_id = db.Column(db.Integer, db.ForeignKey('writer.id'))
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'))
    enum_id = db.Column(db.Integer, db.ForeignKey('connection_enum.id'))

    writer = db.relationship('Writer', backref='connections')
    edition = db.relationship('Edition')
    enum = db.relationship('ConnectionEnum')

    def __repr__(self):
        return f'<{self.writer.name} was {self.type.type} on {self.edition}>'


class ConnectionEnum(Base, EnumMixin):
    """For connection writers to texts and editions."""
    id = db.Column(db.Integer, primary_key=True)


# Content Models
class LineEnum(Base, EnumMixin):
    id = db.Column(db.Integer, primary_key=True)
    display = db.Column(db.String(64), index=True)


class Line(SearchableMixin, Base):
    __searchable__ = ['line', 'text_title']

    id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    num = db.Column(db.Integer, index=True)
    label_id = db.Column(db.Integer, db.ForeignKey('line_enum.id'), index=True)
    lvl1 = db.Column(db.Integer, index=True)
    lvl2 = db.Column(db.Integer, index=True)
    lvl3 = db.Column(db.Integer, index=True)
    lvl4 = db.Column(db.Integer, index=True)
    em_id = db.Column(db.Integer, db.ForeignKey('line_enum.id'), index=True)
    line = db.Column(db.String(200))

    edition = db.relationship('Edition')
    text = db.relationship('Text', secondary='edition', uselist=False)
    label = db.relationship('LineEnum', foreign_keys=[label_id])
    em_status = db.relationship('LineEnum', foreign_keys=[em_id])
    context = db.relationship(
        'Line', primaryjoin='and_(remote(Line.num)<=Line.num+1,'
        'remote(Line.num)>=Line.num-1,'
        'remote(Line.edition_id)==Line.edition_id)',
        foreign_keys=[num, edition_id], remote_side=[num, edition_id],
        uselist=True, viewonly=True)
    annotations = db.relationship(
        'Annotation', secondary='edit',
        primaryjoin='and_(Edit.first_line_num<=foreign(Line.num),'
        'Edit.last_line_num>=foreign(Line.num),'
        'Edit.edition_id==foreign(Line.edition_id),Edit.current==True)',
        secondaryjoin='and_(foreign(Edit.entity_id)==Annotation.id,'
        'Annotation.active==True)', foreign_keys=[num, edition_id],
        uselist=True, lazy='dynamic')

    def __repr__(self):
        return f'<l{self.num} {self.edition.text.title} [{self.label.display}]>'

    def __getattr__(self, attr):
        if attr.startswith('text_'):
            return getattr(self.edition.text, attr.replace('text_', '', 1))
        else:
            raise AttributeError(f"No such attribute {attr}")

    def get_prev_page(self):
        line = None
        if self.lvl4 > 1:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2,
                Line.lvl3 == self.lvl3,
                Line.lvl4 == self.lvl4-1).first()
        elif self.lvl3 > 1:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2,
                Line.lvl3 == self.lvl3-1).order_by(Line.num.desc()).first()
        elif self.lvl2 > 1:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2-1).order_by(Line.num.desc()).first()
        elif self.lvl1 > 1:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1-1).order_by(Line.num.desc()).first()
        return line.get_url() if line else None

    def get_next_page(self):
        line = None
        lvl1 = 0
        lvl2 = 0
        lvl3 = 0
        lvl4 = 0
        if self.lvl4 != 0:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2,
                Line.lvl3 == self.lvl3,
                Line.lvl4 == self.lvl4+1).order_by(Line.num.desc()).first()
            lvl4 = 1
        if self.lvl3 != 0 and not line:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2,
                Line.lvl3 == self.lvl3+1,
                Line.lvl4 == lvl4).order_by(Line.num.desc()).first()
            lvl3 = 1
        if self.lvl2 != 0 and not line:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1,
                Line.lvl2 == self.lvl2+1,
                Line.lvl3 == lvl3,
                Line.lvl4 == lvl4).order_by(Line.num.desc()).first()
            lvl2 = 1
        if self.lvl1 != 0 and not line:
            line = Line.query.filter(
                Line.edition_id == self.edition_id,
                Line.lvl1 == self.lvl1+1,
                Line.lvl2 == lvl2,
                Line.lvl3 == lvl3,
                Line.lvl4 == lvl4).order_by(Line.num.desc()).first()
        return line.get_url() if line else None

    def get_url(self):
        lvl1 = self.lvl1 if self.lvl1 > 0 else None
        lvl2 = self.lvl2 if self.lvl2 > 0 else None
        lvl3 = self.lvl3 if self.lvl3 > 0 else None
        lvl4 = self.lvl4 if self.lvl4 > 0 else None
        return url_for(
            'main.read', text_url=self.edition.text.url,
            edition_num=self.edition.num, l1=lvl1, l2=lvl2, l3=lvl3, l4=lvl4)


# Text Requests
class TextRequestVote(Base, VoteMixin):
    id = db.Column(db.Integer, primary_key=True)
    text_request_id = db.Column(
        db.Integer, db.ForeignKey('text_request.id', ondelete='CASCADE'),
        index=True)
    text_request = db.relationship(
        'TextRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.text_request}"


class TextRequest(Base):
    id = db.Column(db.Integer, primary_key=True)
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


# Tag Requests
class TagRequestVote(Base, VoteMixin):
    id = db.Column(db.Integer, primary_key=True)
    tag_request_id = db.Column(
        db.Integer, db.ForeignKey('tag_request.id', ondelete='CASCADE'),
        index=True)
    tag_request = db.relationship(
        'TagRequest', backref=backref('ballots', passive_deletes=True))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.tag_request}"


class TagRequest(Base):
    id = db.Column(db.Integer, primary_key=True)
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
