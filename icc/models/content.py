import inspect
import sys
import string

from datetime import datetime

from flask import url_for

from sqlalchemy import orm
from sqlalchemy.orm import backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy

from icc import db
from icc.models.mixins import Base, EnumMixin, SearchableMixin
from icc.models.wiki import Wiki


EMPHASIS = ('nem', 'oem', 'em', 'cem')
EMPHASIS_REVERSE = {val:ind for ind,val in enumerate(EMPHASIS)}

WRITERS = ('author', 'editor', 'translator')
WRITERS_REVERSE = {val:ind for ind,val in enumerate(WRITERS)}


class Writer(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    last_name = db.Column(db.String(128), index=True)
    birth_date = db.Column(db.Date, index=True)
    death_date = db.Column(db.Date, index=True)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    wiki = db.relationship('Wiki', backref=backref('writer', uselist=False))
    annotations = db.relationship(
        'Annotation', secondary='join(WriterConnection, Edition)',
        primaryjoin='Writer.id==WriterConnection.writer_id',
        secondaryjoin='Annotation.edition_id==Edition.id', lazy='dynamic')


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

    @classmethod
    def get_by_url(cls, url):
        return cls.query.filter_by(title=url.replace('_', ' '))


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
    text_title = association_proxy('text', 'title')
    writers = association_proxy('connections', 'writer')

    @staticmethod
    def check_section_argument(section):
        if not isinstance(section, tuple):
            raise TypeError("The argument must a tuple of integers.")
        if not all(isinstance(n, int) for n in section):
            raise TypeError("The section tuple must consist of only integers.")

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = 'This wiki is blank.' if not description else description
        super().__init__(*args, **kwargs)
        self.title = f'{self.text_title} - Primary Edition*'\
            if self.primary else f'{self.text_title} - Edition #{self.num}'
        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def init_on_load(self):
        self.title = f'{self.text_title}*'\
            if self.primary else f'{self.text_title} - Edition #{self.num}'

    def __repr__(self):
        return f'<Edition #{self.num} {self.text.title}>'

    def __str__(self):
        return self.title

    def section(self, section):
        """Returns a base query of all the edition's lines in the particular
        hierarchical toc section.
        """
        Edition.check_section_argument(section)

        queries = []
        for precedence, num in enumerate(section):
            queries.append(self.lines\
                           .join(LineAttribute)\
                           .filter(LineAttribute.precedence==precedence+1,
                                   LineAttribute.num==num))
        query = queries[0].intersect(*queries[1:])

        return query

    def prev_section(self, section):
        """Returns the header for the previous section else None."""
        Edition.check_section_argument(section)
        header = self.section(section).first()
        num = header.attrs[len(section)].num
        prev_section = self.toc_by_precedence(len(section))\
            .filter(Line.num<header.num)\
            .order_by(Line.id.desc()).first()
        return prev_section

    def next_section(self, section):
        """Returns the header line for the next section else None."""
        Edition.check_section_argument(section)
        header = self.section(section).first()
        next_section = self.toc_by_precedence(len(section))\
            .filter(Line.num>header.num).first()
        return next_section

    def toc(self):
        """Returns a base query for all of the toc headings of the edition."""
        return self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence>0,
                    LineAttribute.primary==True)

    def toc_by_precedence(self, precedence):
        """Returns a base query for all of the toc headings of the edition of a
        particular precedence (e.g., if the precedence is 2, only return
        headings of second level precedence).
        """
        return self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence==precedence,
                    LineAttribute.primary==True)

    def deepest_precedence(self):
        line = self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence==0,
                    LineAttribute.primary==True).first()
        return len(line.section())

    @property
    def url(self):
        """Returns the url for the object's main view page."""
        return url_for('main.edition', text_url=self.text.url,
                       edition_num=self.num)


class WriterConnection(Base):
    id = db.Column(db.Integer, primary_key=True)
    writer_id = db.Column(db.Integer, db.ForeignKey('writer.id'))
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'))
    enum_id = db.Column(db.Integer)

    writer = db.relationship('Writer',
                             backref=backref('connections', lazy='dynamic'))
    edition = db.relationship('Edition',
                              backref=backref('connections', lazy='dynamic'))
    text = association_proxy('edition', 'text')

    def __repr__(self):
        return f'<{self.writer.name} was the {self.enum} of {self.edition}>'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum = WRITERS[self.enum_id]

    @orm.reconstructor
    def init_on_load(self):
        self.enum = WRITERS[self.enum_id]


class LineEnum(Base, EnumMixin):
    id = db.Column(db.Integer, primary_key=True)
    display = db.Column(db.String(64))

    def __repr__(self):
        return f'<LineEnum {self.display}>'


class LineAttribute(Base):
    """An association class between LineEnum and Line."""
    line_id = db.Column(db.Integer, db.ForeignKey('line.id'), nullable=False,
                        index=True, primary_key=True)
    enum_id = db.Column(db.Integer, db.ForeignKey('line_enum.id'),
                        nullable=False, index=True, primary_key=True)
    num = db.Column(db.Integer, default=1)
    precedence = db.Column(db.Integer, default=1, index=True)
    primary = db.Column(db.Boolean, nullable=False, default=False, index=True)

    enum_obj = db.relationship('LineEnum', backref=backref('attrs',
                                                           lazy='dynamic'))
    # the backref is a dictionary
    line = db.relationship(
        'Line', backref=backref(
            'attrs',
            collection_class=attribute_mapped_collection('precedence')))

    enum = association_proxy('enum_obj', 'enum')
    display = association_proxy('enum_obj', 'display')

    def __repr__(self):
        if self.num:
            return f'<Attr {self.display} {self.num}>'
        else:
            return f'<Attr {self.display}>'


class Line(SearchableMixin, Base):
    __searchable__ = ['line', 'text_title']

    id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    num = db.Column(db.Integer, index=True)
    em_id = db.Column(db.Integer)  # the emphasis id number
    line = db.Column(db.String(200))

    edition = db.relationship('Edition', backref=backref('lines',
                                                         lazy='dynamic'))
    text = association_proxy('edition', 'text')
    text_title = association_proxy('edition', 'text_title')


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
        return (f"<l{self.num} {self.edition.text.title}"
                f"[{self.primary.display}]>")

    @orm.reconstructor
    def init_on_load(self):
        self.emphasis = EMPHASIS[self.em_id]

        for attr in self.attrs.values():
            if attr.primary:
                self.primary = attr

    def section(self):
        return tuple(i.num for i in self.attrs.values() if i.precedence > 0)

    def get_url(self):
        return url_for('main.read', text_url=self.text.url,
                       edition_num=self.edition.num, section=self.section())


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
