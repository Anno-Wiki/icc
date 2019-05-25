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
from icc.models.mixins import (Base, EnumeratedMixin, SearchableMixin,
                               FollowableMixin, LinkableMixin)
from icc.models.wiki import Wiki


# These 2 sets of tuples/dictionaries are for enumerated types that don't need
# an entire enum class in the database (for which it would be a waste of
# resources, etc)
EMPHASIS = ('nem', 'oem', 'em', 'cem')

WRITERS = ('author', 'editor', 'translator')
WRITERS_REVERSE = {val: idx for idx, val in enumerate(WRITERS)}


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

    @classmethod
    def get_object_by_link(cls, name):
        """Get the object by the name."""
        if not cls.__linkable__:
            raise AttributeError("Class does not have a __linkable__ "
                                 "attribute.")
        obj = cls.query.filter(getattr(cls, cls.__linkable__)==name).first()
        return obj

    @classmethod
    def link(cls, name):
        """Override the LinkableMixin link method."""
        idents = name.split(':')
        obj = cls.get_object_by_link(idents[0])
        if not obj:
            return name
        else:
            if len(idents) == 1:
                return f'<a href="{obj.url}">{name}</a>'
            else:
                try:
                    return obj.link_edition(idents[1:])
                except AttributeError:
                    return name

    def link_edition(self, idents):
        """This is specifically to link other editions and line numbers."""
        edition_num = idents[0] if idents[0].isdigit() else 1
        edition = self.editions.filter_by(num=edition_num).first()
        if not edition:
            raise AttributeError("No edition.")
        line_nums = None
        for ident in idents:
            if 'l' in ident:
                line_nums = ident
        if line_nums:
            url = url_for('main.lines', text_url=self.url_name,
                          edition_num=edition_num, nums=line_nums)
            return f"<a href=\"{url}\">{str(edition)} {line_nums}</a>"
        else:
            return f"<a href=\"{edition.url}\">{str(edition)}</a>"

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
    primary : bool
        A boolean switch to represent whether or not the specific edition is the
        primary edition for it's parent text. Only one *should* be primary. If
        more than one is primary, this is an error and needs to be corrected.
    published : DateTime
        The publication date of the specific edition.
    timestamp : DateTime
        Simple timestamp for when the Edition was created.
    connections : BaseQuery
        A filterable BaseQuery of WriterConnections.
    text_title : str
        A proxy for the title of the text. Mostly used so that the Annotation
        can query it easily with it's own association_proxy.
    tochide : boolean
        A flag for disabling the showing of the toc dispay enum because the toc
        body is complete on it's own.
    verse : boolean
        A flag for disabling the line concatenation that happens on cell phones.
        It will eventually become (either) more useful, or less. Unsure yet.
    """
    @staticmethod
    def _check_section_argument(section):
        """Static helper method for throwing section errors."""
        if not isinstance(section, tuple):
            raise TypeError("The argument must a tuple of integers.")
        if not all(isinstance(n, int) for n in section):
            raise TypeError("The section tuple must consist of only integers.")

    _title = db.Column(db.String(235), default=None)
    num = db.Column(db.Integer, default=1)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id'))
    primary = db.Column(db.Boolean, default=False)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)
    published = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    tochide = db.Column(db.Boolean, default=True)
    verse = db.Column(db.Boolean, default=False)

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
        if self._title:
            return f'{self._title}*' if self.primary else self._title
        return (f'{self.text_title}*' if self.primary else
                f"{self.text_title} - Ed. #{self.num}")

    @property
    def edition_title(self):
        """A string for the edition similar to title but *not* including the
        parent text's title.
        """
        if self._title:
            return f'{self._title}*' if self.primary else self._title
        return (f"Edition #{self.num} - Primary" if self.primary else
                f"Edition #{self.num}")

    def __init__(self, *args, **kwargs):
        """Creates a wiki for the edition with the provided description."""
        description = kwargs.pop('description', None)
        description = 'This wiki is blank.' if not description else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    @orm.reconstructor
    def __init_on_load__(self):
        """Creates a defaultdict of lists of writers based on their connection
        type (e.g., author, editor, translator, etc.)
        """
        self.writers = defaultdict(list)
        for conn in self.connections.all():
            self.writers[conn.enum].append(conn.writer)

    def __repr__(self):
        return f'<{self.title}>'

    def __str__(self):
        return self.title

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

    def get_lines(self, nums):
        if len(nums) >= 2:
             line_query = self.lines.filter(Line.num>=nums[0],
                                            Line.num<=nums[-1])
        else:
             line_query = self.lines.filter(Line.num==nums[0])
        return line_query


class Writer(Base, FollowableMixin, LinkableMixin):
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
    __linkable__ = 'name'

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
    def __init_on_load__(self):
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
    def __init_on_load__(self):
        """Resolves the enum_id to the enum."""
        self.enum = WRITERS[self.enum_id]

    def __repr__(self):
        return f'<{self.writer.name} was the {self.enum} of {self.edition}>'


class TOC(EnumeratedMixin, Base):
    num = db.Column(db.Integer, index=True)
    precedence = db.Column(db.Integer, default=1, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('toc.id'), index=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    body = db.Column(db.String(200), index=True)

    parent = db.relationship('TOC', uselist=False, remote_side='TOC.id',
                             backref=backref('children',
                                             remote_side='TOC.parent_id'))
    edition = db.relationship('Edition', backref=backref('toc', lazy='dynamic'))
    text = association_proxy('edition', 'text')

    def __repr__(self):
        return f'<{self.enum} {self.num} of {self.edition}>'

    def __str__(self):
        return self.body


class Line(EnumeratedMixin, SearchableMixin, Base):
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
    num : int
        The line number within the edition.
    em : str
        A string corresponding to an enumerated type describing emphasis status.
        See On Emphasis in the wiki
    toc : TOC
        The section the line is in in the TOC. See On the TOC in the Wiki.
    body : str
        The actual text of the line. Processed in my processor.
    text : Text
        An association proxy to the text for ease of reference.
    text_title : str
        The title of the parent text of the edition the line is in.
    edition : Edition
        The edition of the parent text.
    context : list
        A list of all line's surrounding lines (+/- 5 lines)
    annotations : BaseQuery
        An SQLA BaseQuery for all the annotations that contain this line in
        their target. It's a nasty relationship.
    """
    __searchable__ = ['body', 'text_title']

    num = db.Column(db.Integer, index=True)
    body = db.Column(db.Text)
    em_id = db.Column(db.Integer)

    toc_id = db.Column(db.Integer, db.ForeignKey('toc.id'), index=True)
    toc = db.relationship('TOC')

    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    edition = db.relationship('Edition', backref=backref('lines',
                                                         lazy='dynamic'))

    text = association_proxy('edition', 'text')
    text_title = association_proxy('edition', 'text_title')

    def __init__(self, *args, **kwargs):
        self.em_id = EMPHASIS.index(kwargs.pop('em'))
        super().__init__(*args, **kwargs)

#    context = db.relationship(
#        'Line', primaryjoin='and_(remote(Line.num)<=Line.num+1,'
#        'remote(Line.num)>=Line.num-1,'
#        'remote(Line.edition_id)==Line.edition_id)',
#        foreign_keys=[num, edition_id], remote_side=[num, edition_id],
#        uselist=True, viewonly=True)
#    annotations = db.relationship(
#        'Annotation', secondary='edit',
#        primaryjoin='and_(Edit.first_line_num<=foreign(Line.num),'
#        'Edit.last_line_num>=foreign(Line.num),'
#        'Edit.edition_id==foreign(Line.edition_id),Edit.current==True)',
#        secondaryjoin='and_(foreign(Edit.entity_id)==Annotation.id,'
#        'Annotation.active==True)', foreign_keys=[num, edition_id],
#        uselist=True, lazy='dynamic')

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
    def __init_on_load__(self):
        """Resolves the em_id to the line's emphasis status."""
        self.emphasis = EMPHASIS[self.em_id]

    def __repr__(self):
        return (f"<l{self.num} {self.edition}>")


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
