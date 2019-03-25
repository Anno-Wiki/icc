"""This module contains all of the content models for the ICC. That is to say,
these models are the text models, the lines of text, the authors, the editions,
etc.

Between this module and the models.annotation we have the core of the entire
app (besides the user system).
"""
import inspect
import sys

from collections import defaultdict
from datetime import datetime

from flask import url_for

from sqlalchemy import orm
from sqlalchemy.orm import backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy

from icc import db
from icc.models.mixins import (Base, EnumMixin, SearchableMixin,
                               FollowableMixin, LinkableMixin)
from icc.models.wiki import Wiki


# These 2 sets of tuples/dictionaries are for enumerated types that don't need
# an entire enum class in the database (for which it would be a waste of
# resources, etc)
EMPHASIS = ('nem', 'oem', 'em', 'cem')
EMPHASIS_REVERSE = {val: ind for ind, val in enumerate(EMPHASIS)}

WRITERS = ('author', 'editor', 'translator')
WRITERS_REVERSE = {val: ind for ind, val in enumerate(WRITERS)}


class Text(Base, FollowableMixin, LinkableMixin):
    __linkable__ = 'title'
    """The text-object. A text is more a categorical, or philosophical concept.
    In essence, a book can have any number of editions, ranging from different
    translations to re-edited or updated versions (which is more common with
    non-fiction texts, and usually just consists of an added
    preface/introduction).

    Because of this dynamic, a text can is just a shell with a wiki that
    editions point to. Editions are the heart of the program. But the Text has a
    primary edition to which all annotations should be directed for a work
    unless they regard textual issues that differ between translations or
    editions.

    Attributes
    ----------
    title : string
        The title string of the object
    sort_title : string
        A string by which these objects will be sorted (i.e., so that it doesn't
        contain modifier words like "the" or "a".
    wiki_id : int
        The id of the wiki object.
    published : Date
        A date corresponding to the publication date of the first edition of the
        text irl.
    timestamp : DateTime
        This is just a timestamp marking when the text was added to the
        database. It's really unnecessary, tbh. Eventually to be eliminated.
    followers : BaseQuery
        An SQLA BaseQuery object for all the followers of the text.
    wiki : :class:`Wiki`
        A wiki object describing the text.
    editions : BaseQuery
        An SQLA BaseQuery object for all the editions pointing to this text.
    primary : :class:`Edition`
        An edition object that represents the primary edition of the text (the
        one we direct all annotations to unless they're about textual issues,
        etc.)
    url : string
        A url string for the main view page of the text object.
    url_name : string
        A string that can be used in a url for the text_url parameter.
    """

    @classmethod
    def get_by_url(cls, url):
        """This is a helper function that takes the output of url_name and
        uses it to get the object that matches it.
        """
        return cls.query.filter_by(title=url.replace('_', ' '))

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

    @property
    def url(self):
        """This returns the actual internally-resolved url for the text's main
        view page.
        """
        return url_for('main.text', text_url=self.url_name)

    @property
    def url_name(self):
        """Returns the name of the object (title) translated in to a
        url-utilizable string (i.e., no spaces).

        Notes
        -----
        This method right now is very simple. The issue might become more
        complex when we have works with titles that have punctuation marks in
        them. eventually we might have to modify this method to translate those
        characters into url-acceptable characters (e.g., escape them).
        """
        return self.title.replace(' ', '_')

    def __init__(self, *args, **kwargs):
        """This init method creates a wiki for the object with the supplied
        description.
        """
        description = kwargs.pop('description', None)
        description = "This wiki is blank." if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Text {self.id}: {self.title}>'

    def __str__(self):
        return self.title


class Edition(Base, FollowableMixin):
    """The Edition model. This is actually more central to the app than the Text
    object. The edition has all of the writer connections, annotations, and
    lines connected to it.

    Attributes
    ----------
    num : int
        The edition number of the edition. I.e., edition 1, 2, etc.
    text_id : int
        The id of the parent text object for the edition.
    primary : bool
        A boolean switch to represent whether or not the specific edition is the
        primary edition for it's parent text. Only one *should* be primary. If
        more than one is primary, this is an error and needs to be corrected.
    wiki_id : int
        The id of the descriptive wiki for the edition.
    published : DateTime
        The publication date of the specific edition.
    timestamp : DateTime
        Simple timestamp for when the Edition was created.
    connections : BaseQuery
        A filterable BaseQuery of WriterConnections.
    wiki : :class:`Wiki`
        The descriptive wiki object for the specific edition.
    text : :class:`Text`
        The parent text object.
    text_title : str
        A proxy for the title of the text. Mostly used so that the Annotation
        can query it easily with it's own association_proxy.
    """
    @staticmethod
    def _check_section_argument(section):
        """Static helper method for throwing section errors."""
        if not isinstance(section, tuple):
            raise TypeError("The argument must a tuple of integers.")
        if not all(isinstance(n, int) for n in section):
            raise TypeError("The section tuple must consist of only integers.")

    num = db.Column(db.Integer, default=1)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id'))
    primary = db.Column(db.Boolean, default=False)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    published = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    annotations = db.relationship('Annotation', lazy='dynamic')
    connections = db.relationship('WriterConnection', lazy='dynamic')
    wiki = db.relationship('Wiki', backref=backref('edition', uselist=False))
    text = db.relationship('Text')
    text_title = association_proxy('text', 'title')

    @property
    def url(self):
        """A string title of the edition. Basically consists of the parent
        text's title and an asterisk for the primary edition or 'Edition #'.
        """
        return url_for('main.edition', text_url=self.text.url_name,
                       edition_num=self.num)

    @property
    def title(self):
        """Returns the title representation string of the edition."""
        return (f"{self.text_title}*" if self.primary else
                f"{self.text_title} - Edition #{self.num}")

    @property
    def edition_title(self):
        """A string for the edition similar to title but *not* including the
        parent text's title.
        """
        return (f"Edition #{self.num} - Primary" if self.primary else
                f"Edition #{self.num}")

    @property
    def deepest_precedence(self):
        """Returns an integer representing the deepest precedence level of the
        edition's toc hierarchy.
        """
        line = self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence==0,
                    LineAttribute.primary==True).first()
        return len(line.section)

    @property
    def toc(self):
        """Returns a base query for all of the toc headings of the edition."""
        return self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence>0,
                    LineAttribute.primary==True)

    def __init__(self, *args, **kwargs):
        """Creates a wiki for the edition with the provided description."""
        description = kwargs.pop('description', None)
        description = 'This wiki is blank.' if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def init_on_load(self):
        """Creates a defaultdict of lists of writers based on their connection
        type (e.g., author, editor, translator, etc.)
        """
        self.writers = defaultdict(list)
        for conn in self.connections.all():
            self.writers[conn.enum].append(conn.writer)

    def __repr__(self):
        return f"<Edition #{self.num} {self.text.title}>"

    def __str__(self):
        return self.title

    def section(self, section):
        """Returns a base query of all the edition's lines in the particular
        hierarchical toc section.
        """
        Edition._check_section_argument(section)

        queries = []
        for precedence, num in enumerate(section):
            queries.append(self.lines
                           .join(LineAttribute)
                           .filter(LineAttribute.precedence==precedence+1,
                                   LineAttribute.num==num))
        query = queries[0].intersect(*queries[1:])

        return query

    def prev_section(self, section):
        """Returns the header for the previous section else None."""
        Edition._check_section_argument(section)
        header = self.section(section).first()
        prev_section = self.toc_by_precedence(len(section))\
            .filter(Line.num<header.num)\
            .order_by(Line.id.desc()).first()
        return prev_section

    def next_section(self, section):
        """Returns the header line for the next section else None."""
        Edition._check_section_argument(section)
        header = self.section(section).first()
        next_section = self.toc_by_precedence(len(section))\
            .filter(Line.num>header.num).first()
        return next_section

    def toc_by_precedence(self, precedence):
        """Returns a base query for all of the toc headings of the edition of a
        particular precedence (e.g., if the precedence is 2, only return
        headings of second level precedence).
        """
        return self.lines\
            .join(LineAttribute)\
            .filter(LineAttribute.precedence==precedence,
                    LineAttribute.primary==True)

    def get_lines(self, nums):
        if len(nums) >= 2:
             line_query = self.lines.filter(Line.num>=nums[0],
                                            Line.num<=nums[-1])
        else:
             line_query = self.lines.filter(Line.num==nums[0])
        return line_query


class Writer(Base, FollowableMixin, LinkableMixin):
    __linkable__ = 'name'

    """The writer model. This used to be a lot more complicated but has become
    fairly elegant. All historical contributors to the text are writers, be they
    editors, translators, authors, or whatever the heck else we end up coming up
    with (perhaps with the exception of annotator, we'll see).

    Attributes
    ----------
    name : string
        The full name of the writer
    family_name : string
        The family name of the writer. We store this as an actual value in the
        db instead of computing it on the fly because of varying naming
        conventions (e.g., Chinese names). And we need it for sorting purposes.
    birth_date : Date
        The birthdate of the writer.
    death_date : Date
        The deathdate of the writer.
    wiki_id : int
        The id of the descriptive wiki object.
    timestamp : datetime
        The timestamp of when the writer was added to the database. Superfluous.
    followers : BaseQuery
        An SQLA BaseQuery of all of the followers of the writer.
    connections : BaseQuery
        An SQLA BaseQuery of all of the connection objects for the writer (i.e.,
        the writer's relationships to various editions).
    wiki : :class:`Wiki`
        The descriptive wiki object.
    annotations : BaseQuery
        An SQLA BaseQuery for all of the annotations on all of the editions the
        writer is responsible for.
    """
    name = db.Column(db.String(128), index=True)
    family_name = db.Column(db.String(128), index=True)
    birth_date = db.Column(db.Date, index=True)
    death_date = db.Column(db.Date, index=True)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    connections = db.relationship('WriterConnection', lazy='dynamic')
    wiki = db.relationship('Wiki', backref=backref('writer', uselist=False))
    annotations = db.relationship(
        'Annotation', secondary='join(WriterConnection, Edition)',
        primaryjoin='Writer.id==WriterConnection.writer_id',
        secondaryjoin='Annotation.edition_id==Edition.id', lazy='dynamic')

    @property
    def url(self):
        """The url for the main view page for the writer."""
        return url_for('main.writer', writer_url=self.url_name)

    @property
    def url_name(self):
        """A string that can be used for urls (i.e., it has all the spaces
        replaced with underscores.
        """
        return self.name.replace(' ', '_')

    def __init__(self, *args, **kwargs):
        """Creates a descriptive wiki as well."""
        description = kwargs.pop('description', None)
        description = 'This writer does not have a biography yet.'\
            if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def init_on_load(self):
        """Creates a dictionary mapping the writer's role to the editions."""
        self.works = defaultdict(list)
        for conn in self.connections.all():
            self.works[conn.enum].append(conn.edition)

    def __repr__(self):
        return f'<Writer: {self.name}>'

    def __str__(self):
        return self.name


class WriterConnection(Base):
    """This is a proxy object that connects writers to editions. It resolves
    enum_id to the role of the writer's connection to the edition based on the
    WRITERS tuple.

    Attributes
    ----------
    writer_id : int
        The id of the writer in the connection.
    edition_id : int
        The id of the edition in the connection.
    enum_id : int
        The id of the enumerated role of the connection.
    writer : :class:`Writer`
        The writer object in the connection
    edition : :class:`Edition`
        The edition object in the connection.
    enum : str
        The enumerated string of the writer's role in the connection.
    """
    writer_id = db.Column(db.Integer, db.ForeignKey('writer.id'))
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'))
    enum_id = db.Column(db.Integer)

    writer = db.relationship('Writer')
    edition = db.relationship('Edition')

    def __init__(self, *args, **kwargs):
        """Resolves the enum_id to the enum."""
        super().__init__(*args, **kwargs)
        self.enum = WRITERS[self.enum_id]

    @orm.reconstructor
    def init_on_load(self):
        """Resolves the enum_id to the enum."""
        self.enum = WRITERS[self.enum_id]

    def __repr__(self):
        return f'<{self.writer.name} was the {self.enum} of {self.edition}>'


class LineEnum(Base, EnumMixin):
    """An enumerated type used to classify line attributes.

    Attributes
    ----------
    enum : str
        A string representing the enum type. Mostly for internal use.
    display : str
        A string for the public display of the attribute. Usually used for
        headings in the toc on edition.html.
    """
    display = db.Column(db.String(64))

    def __repr__(self):
        return f'<LineEnum {self.display}>'


class LineAttribute(Base):
    """An association class between LineEnum and Line."""
    line_id = db.Column(db.Integer, db.ForeignKey('line.id'), nullable=False,
                        index=True)
    enum_id = db.Column(db.Integer, db.ForeignKey('lineenum.id'),
                        nullable=False, index=True)
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
    """A line. This is actually a very important class. It is the only
    searchable type so far. Eventually this won't be the case. Then I'll have to
    remember to update this comment. I probably will forget... So if this
    comment is no longer true, please modify it.

    Attributes
    ----------
    __searchable__ : list
        A list of strings that correspond to the attributes that should be
        indexed in elasticsearch. It's defined by :class:`SearchableMixin` so
        see that for more information.
    edition_id : int
        The id of the edition the line is in.
    num : int
        The line number within the edition.
    em_id : int
        The enumerated id number of the emphasis status of the line. See the
        tuple EMPHASIS for more clarity. Also see the wiki on emphasis.
    line : str
        The actual text of the line. Processed in my processor.
    text : class:`Text`
        An association proxy to the text for ease of reference.
    text_title : str
        The title of the parent text of the edition the line is in.
    context : list
        A list of all line's surrounding lines (+/- 5 lines)
    annotations : BaseQuery
        An SQLA BaseQuery for all the annotations that contain this line in
        their target. It's a nasty relationship.
    """
    __searchable__ = ['line', 'text_title']

    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    num = db.Column(db.Integer, index=True)
    em_id = db.Column(db.Integer)
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

    @property
    def url(self):
        """The url for the smallest precedence section to read, in is the
        line.
        """
        return url_for('main.read', text_url=self.text.url_name,
                       edition_num=self.edition.num, section=self.section)

    @property
    def section(self):
        """A tuple of the section numbers."""
        return tuple(i.num for i in self.attrs.values() if i.precedence > 0)

    @orm.reconstructor
    def init_on_load(self):
        """Resolves the em_id to the line's emphasis status."""
        self.emphasis = EMPHASIS[self.em_id]
        for attr in self.attrs.values():
            if attr.primary:
                self.primary = attr

    def __repr__(self):
        return (f"<l{self.num} {self.edition.text.title}"
                f"[{self.primary.display}]>")


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
