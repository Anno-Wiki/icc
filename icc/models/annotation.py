"""This module contains all of the annotation models for the ICC.

Essentially, anything that is required to render an annotation.
"""

import sys
import inspect
from datetime import datetime
from hashlib import sha1
from math import log10

from sqlalchemy import orm
from sqlalchemy.orm import backref
from flask import url_for, flash, current_app as app

from icc import db
from icc.models.mixins import (Base, VoteMixin, EditMixin, FollowableMixin,
                               FlagMixin, LinkableMixin, VotableMixin)
from icc.models.wiki import Wiki


class Tag(Base, FollowableMixin, LinkableMixin):
    __linkable__ = 'tag'
    """A class representing tags.

    Attributes
    ----------
    tag : str
        The name of the tag
    locked : bool
        The locked status of the tag (i.e., whether it is available for ordinary
        users to apply to their annotations).
    wiki_id : int
        The id of the tag's wiki.
    wiki : :class:`Wiki`
        The tag's :class:`Wiki` object.
    annotations : :class:`BaseQuery`
        A :class:`BaseQuery` object of all of the annotations which currently
        have this tag applied to them.
    """
    @classmethod
    def intersect(cls, tags):
        """Get the annotations at the intersection of multiple tags.

        Parameters
        ----------
        tags : tuple
            A tuple of strings corresponding to the names of the tags to be
            intersected.

        Returns
        -------
        :class:`BaseQuery`
            A :class:`BaseQuery` object that can be used to get all of the
            annotations.

        Raises
        ------
        TypeError
            If the first argument is not a tuple.
        TypeError
            If the elements of the tuple are not all strings.
        """
        if not isinstance(tags, tuple):
            raise TypeError('Tags argument must be a tuple of strings.')
        if not all(isinstance(tag, str) for tag in tags):
            raise TypeError("The tags tuple must consist of only strings.")

        queries = []
        for tag in tags:
            queries.append(cls.query.filter_by(tag=tag).first().annotations)
        query = queries[0].intersect(*queries[1:])
        return query

    @classmethod
    def union(cls, tags):
        """Get the annotations at the union of multiple tags.

        Parameters
        ----------
        tags : tuple
            A tuple of strings corresponding to the names of the tags to be
            unioned.

        Returns
        -------
        BaseQuery
            A :class:`BaseQuery` object that can be used to get all of the
            annotations.

        Raises
        ------
        TypeError
            If the first argument is not a tuple.
        TypeError
            If the elements of the tuple are not all strings.
        """
        if not isinstance(tags, tuple):
            raise TypeError('Tags argument must be a tuple of strings.')
        if not all(isinstance(tag, str) for tag in tags):
            raise TypeError("The tags tuple must consist of only strings.")

        queries = []
        for tag in tags:
            queries.append(cls.query.filter_by(tag=tag).first().annotations)
        query = queries[0].union(*queries[1:])
        return query

    tag = db.Column(db.String(128), index=True, unique=True)
    locked = db.Column(db.Boolean, default=False)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)

    wiki = db.relationship('Wiki', backref=backref('tag', uselist=False))
    annotations = db.relationship(
        'Annotation', secondary='join(tags, Edit, and_(tags.c.edit_id==Edit.id,'
        'Edit.current==True))', primaryjoin='Tag.id==tags.c.tag_id',
        secondaryjoin='and_(Edit.entity_id==Annotation.id,'
        'Annotation.active==True)', lazy='dynamic', passive_deletes=True)

    @property
    def url(self):
        """The url for the main view page for the tag."""
        return url_for('main.tag', tag=self.tag)

    def __init__(self, *args, **kwargs):
        """Creation of a tag also creates a :class:`Wiki`."""
        description = kwargs.pop('description', None)
        description = ("This tag has no description yet." if not description
                       else description)
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Tag {self.id}: {self.tag}>'

    def __str__(self):
        return f'<tag>{self.tag}</tag>'


class Comment(Base):
    """A class representing comments on annotations.

    Attributes
    ----------
    poster_id : int
        The id of the user who posted the comment.
    annotation_id : int
        The id of the annotation the comment is applied to.
    parent_id : int
        The id of the parent comment (None if it is a top level comment, i.e., a
        thread).
    depth : int
        The depth level of the comment in a thread.
    weight : int
        The weight of the comment.
    body : str
        The body of the comment.
    timestamp : datetime
        When the comment was posted, in the utc timezone.
    poster : User
        The user who posted the comment.
    annotation : Annotation
        The annotation the comment is on.
    parent : Comment
        The parent of the comment.
    children : BaseQuery
        The immediate children of the comment.
    """

    poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True,
                          nullable=False)
    annotation_id = db.Column(
        db.Integer, db.ForeignKey('annotation.id', ondelete='CASCADE'),
        index=True, nullable=False)
    parent_id = db.Column(
        db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), index=True,
        default=None)
    depth = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    poster = db.relationship('User', backref=backref('comments',
                                                     lazy='dynamic'))
    annotation = db.relationship('Annotation',
                                 backref=backref('comments', lazy='dynamic',
                                                 passive_deletes=True))
    parent = db.relationship(
        'Comment', remote_side='Comment.id', uselist=False,
        backref=backref('children', remote_side=[parent_id], lazy='dynamic'))

    def __repr__(self):
        return f'<Comment {self.id} on [{self.annotation_id}]>'


class AnnotationVote(Base, VoteMixin):
    """A class that represents a user's vote on an annotation.

    Attributes
    ----------
    annotation_id : int
        The id of the annotation voted on.
    reputationchange_id : int
        The id of the :class:`ReputationChange` object that accompanies the
        :class:`Vote`.
    entity : :class:`Annotation`
        The :class:`Annotation` the vote has been applied to.
    repchange : :class:`ReputationChange`
        The :class:`ReputationChange`

    The Vote class also possesses all of the attributes of :class:`VoteMixin`.
    """
    annotation_id = db.Column(
        db.Integer, db.ForeignKey('annotation.id', ondelete='CASCADE'),
        index=True)
    reputationchange_id = db.Column(
        db.Integer, db.ForeignKey('reputationchange.id', ondelete='CASCADE'))

    entity = db.relationship('Annotation')
    repchange = db.relationship('ReputationChange',
                                backref=backref('vote', uselist=False))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.entity}"


class AnnotationFlag(Base, FlagMixin):
    """A flagging event for annotations. Uses the AnnotationFlagEnum for
    templating. Will need an update soon to overhaul the flagging system to be
    more public.

    Inherits
    --------
    FlagMixin

    Attributes
    ----------
    annotation_id : int
        The int of the :class:`Annotation` object the flag is applied to.
    entity : :class:`Annotation`
        The actual annotation.
    """
    annotation_id = db.Column(db.Integer,
                              db.ForeignKey('annotation.id',
                                            ondelete='CASCADE'), index=True)
    entity = db.relationship('Annotation', backref=backref('flags',
                                                           lazy='dynamic'))


class Annotation(Base, FollowableMixin, LinkableMixin, VotableMixin):
    __vote__ = AnnotationVote
    __reputable__ = 'annotator'

    __linkable__ = 'id'

    """And now, the moment you've been waiting for, the star of the show: the
    main Annotation data class.

    Attributes
    ----------
    weight : int
        The weight of the annotation in upvotes/downvotes.
    timestamp : datetime
        The UTC date time when the annotation was first created.
    locked : bool
        The flag that indicates whether the annotation is locked from editing.
    active : bool
        The flag that indicates the annotation has been deactivated from
        viewing.
    ballots : BaseQuery
        An SQLA BaseQuery of all of the ballots that have been cast for this
        annotation.
    annotator : :class`User`
        The user object of the user who annotated the annotation to begin with.
    first_line : :class:`Line`
        The first line of the target of the annotation. I don't know why this is
        here. I don't know what I use it for. TBD.
    edition : :class:`Edition`
        The edition object the annotation is applied to.
    text : :class:`Text`
        The text object the edition belongs to upon which the annotation is
        annotated.
    HEAD : :class:`Edit`
        The edit object that is the current version of the annotation object. I
        want to eventually change this to current, and it seems like it would
        not be hard. But I am hesitant to do it because then it would not be
        unique, and it would no longer be easy to change. All it requires to
        change is a `find . -type f | xargs sed -i 's/HEAD/current/g'` command
        in the root directory of the project and the change would be complete.
        But since there are other objects which use the current designation
        (namely, :class:`Wiki`), once this command is applied and committed,
        there's really no going back without manually finding it. So for now,
        this is where it's staying.
    edits : list
        All of the edits which have been approved.
    history : list
        All of the edits which have been approved, dynamically.
    all_edits : list
        All of the edits. All of them. Like, every one of them, period.
    edit_pending : list
        A list of edits which are neither approved, nor rejected. Essentially,
        this just serves to indicate as a bool-like list object that there is an
        edit pending, because the system is designed never to allow more than
        one edit pending at a time. This is, in fact, false, and I need to go
        through the system and fix the bug whereby a user could surreptitiously
        cause a race condition and have two edits submitted at the same time.
    lines : list
        A list of all of the lines that are the target of the annotation.
    context : list
        A list of all the lines that are the target of the annotation *plus*
        five lines on either side of the first and last lines of the target
        lines.
    flag_history : list
        A list of all of the :class:`AnnotationFlag`s which have been applied to
        the annotation.
    active_flags : list
        A list of all of the flags that are currently active on the annotation.

    Notes
    -----
    The four edit lists are redundant and will need to be eliminated and
    whittled down. There should only be three: the approved edit history, the
    rejected edits, and the pending edits. There's no reason for anything else.
    Even the rejected edits are actually useless. I think I'll leave that out.
    Never is better than right now.

    The flags will also have to be refined. I want to make the flag system more
    public-facing, like Wikipedia's warning templates.

    And finally, the lines could possibly be changed. The context, for instance,
    might be prior-context and posterior-context, or something of that nature,
    instead of packing the same lines into the same list. Perhaps not. TBD.
    """
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    weight = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    ballots = db.relationship('AnnotationVote', lazy='dynamic')
    annotator = db.relationship('User')
    first_line = db.relationship(
        'Line', secondary='edit', primaryjoin='Edit.entity_id==Annotation.id',
        secondaryjoin='and_(Line.edition_id==Annotation.edition_id,'
        'Edit.first_line_num==Line.num)', uselist=False)

    edition = db.relationship('Edition')
    text = db.relationship('Text', secondary='edition',
                           backref=backref('annotations', lazy='dynamic'),
                           uselist=False)

    # relationships to `Edit`
    HEAD = db.relationship('Edit', primaryjoin='and_(Edit.current==True,'
                           'Edit.entity_id==Annotation.id)', uselist=False)

    edits = db.relationship(
        'Edit',
        primaryjoin='and_(Edit.entity_id==Annotation.id, Edit.approved==True)',
        passive_deletes=True)
    history = db.relationship(
        'Edit',
        primaryjoin='and_(Edit.entity_id==Annotation.id, Edit.approved==True)',
        lazy='dynamic', passive_deletes=True)
    all_edits = db.relationship(
        'Edit', primaryjoin='Edit.entity_id==Annotation.id', lazy='dynamic',
        passive_deletes=True)
    edit_pending = db.relationship(
        'Edit',
        primaryjoin='and_(Edit.entity_id==Annotation.id, Edit.approved==False, '
        'Edit.rejected==False)',
        passive_deletes=True)

    # relationships to `Line`
    lines = db.relationship(
        'Line', secondary='edit',
        primaryjoin='and_(Annotation.id==Edit.entity_id,Edit.current==True)',
        secondaryjoin='and_(Line.num>=Edit.first_line_num,'
        'Line.num<=Edit.last_line_num,Line.edition_id==Annotation.edition_id)',
        viewonly=True, uselist=True)
    context = db.relationship(
        'Line', secondary='edit',
        primaryjoin='and_(Annotation.id==Edit.entity_id,Edit.current==True)',
        secondaryjoin='and_(Line.num>=Edit.first_line_num-5,'
        'Line.num<=Edit.last_line_num+5,'
        'Line.edition_id==Annotation.edition_id)', viewonly=True, uselist=True)

    # Relationships to `Flag`
    flag_history = db.relationship(
        'AnnotationFlag',
        primaryjoin='Annotation.id==AnnotationFlag.annotation_id',
        lazy='dynamic')
    active_flags = db.relationship(
        'AnnotationFlag',
        primaryjoin='and_(Annotation.id==AnnotationFlag.annotation_id,'
        'AnnotationFlag.resolver_id==None)', passive_deletes=True)

    @property
    def url(self):
        return url_for('main.annotation', annotation_id=self.id)

    @property
    def readable_weight(self):
        """This property produces a readable weight, rather than a computer-like
        int. The readable weight modulates based on the thousand and million.
        """
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f'{round(self.weight/1000000,1)}m'
        elif self.weight >= 1000 or self.weight <= -1000:
            return f'{round(self.weight/1000,1)}k'
        else:
            return f'{self.weight}'

    def __init__(self, *ignore, edition, annotator, locked=False, fl, ll, fc,
                 lc, body, tags):
        """This init method creates the initial :class:`Edit` object. This
        reduces friction in creating annotations.
        """
        params = [edition, annotator, fl, ll, fc, lc, body, tags]
        if ignore:
            raise TypeError("Positional arguments not accepted.")
        elif None in params:
            raise TypeError("Keyword arguments cannot be None.")
        elif not type(tags) == list:
            raise TypeError("Tags must be a list of tags.")
        super().__init__(edition=edition, annotator=annotator, locked=locked)
        current = Edit(
            annotation=self, approved=True, current=True, editor=annotator,
            edition=edition, first_line_num=fl, last_line_num=ll,
            first_char_idx=fc, last_char_idx=lc, body=body, tags=tags, num=0,
            reason="initial version")
        db.session.add(current)
        self.HEAD = current

    def edit(self, *ignore, editor, reason, fl, ll, fc, lc, body, tags):
        """This method creates an edit for the annotation. It is much more
        transparent than creating the edit independently.
        """
        params = [editor, reason, fl, ll, fc, lc, body, tags]
        if ignore:
            raise TypeError("Positional arguments not accepted.")
        elif None in params:
            raise TypeError("Keyword arguments cannot be None.")
        elif not isinstance(tags, list):
            raise TypeError("Tags must be a list of tags.")
        elif not all(isinstance(tag, Tag) for tag in tags):
            raise TypeError("Tags must be a list of tag objects.")
        edit = Edit(
            edition=self.edition, editor=editor, num=self.HEAD.num+1,
            reason=reason, annotation=self, first_line_num=fl, last_line_num=ll,
            first_char_idx=fc, last_char_idx=lc, body=body, tags=tags)
        if edit.hash_id == self.HEAD.hash_id:
            flash("Your suggested edit is no different from the previous "
                  "version.")
            return False
        elif editor == self.annotator or\
                editor.is_authorized('immediate_edits'):
            edit.approved = True
            self.HEAD.current = False
            edit.current = True
            flash("Edit approved.")
        else:
            flash("Edit submitted for review.")
        db.session.add(edit)
        return True

    def up_power(self, voter):
        """An int that represents the user's current upvote power.

        This is currently set to 10log10 of the user's reputation, floored at 1.
        """
        if voter.reputation <= 1:
            return 1
        else:
            return int(10*log10(voter.reputation))

    def down_power(self, voter):
        """An int of the user's down power. This is simply half of the user's up
        power, but at least one.
        """
        power = self.up_power(voter)
        if power / 2 <= 1:
            return -1
        else:
            return -int(power)


class EditVote(Base, VoteMixin):
    """A vote on an :class:`Edit`. They are used to determine whether the edit
    should be approved. Only user's with a reputation above a certain threshold
    (or with a certain right) are supposed to be able to apply these (or review
    annotation edits at all). This might, or might not, be the case.
    I will have to add assurances.


    Attributes
    ----------
    edit_id : int
        The id of the :class:`Edit` the vote is applied to.
    edit : :class:`Edit`
        The edit object the vote was applied to.
    reputationchange_id : int
        The id of the :class:`ReputationChange` object associated with the edit
        (if the edit is approved).
    repchange : :class:`ReputationChange`
        The reputation change object associated with the edit vote if it is an
        approval vote (i.e., above a certain threshold of votes or applied by
        someone with immediate edit approval rights.

    The EditVote class also possesses all of the attributes of
    :class:`VoteMixin`.
    """
    edit_id = db.Column(db.Integer,
                        db.ForeignKey('edit.id', ondelete='CASCADE'),
                        index=True)
    entity = db.relationship('Edit', backref=backref('ballots', lazy='dynamic',
                                                     passive_deletes=True))
    reputationchange_id = db.Column(db.Integer,
                                    db.ForeignKey('reputationchange.id'),
                                    default=None)
    repchange = db.relationship('ReputationChange',
                                backref=backref('edit_vote', uselist=False))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.edit}"


class Edit(Base, EditMixin, VotableMixin):
    __vote__ = EditVote
    __reputable__ = 'editor'
    """The Edit class, which represents the current state of an
    :class:`Annotation`. An annotation object is just a HEAD, like in git. Or,
    rather, a tag? I can't remember how git's model works, but essentially, the
    annotation object just serves as a pointer to it's current edit.

    Attributes
    ----------
    edition_id : int
        The id of the edition to which the annotation is applied. This column is
        *technically* redundant, but it simplifies some operations. I may
        eventually (probably sooner than later, actually, now that I know about
        SQLA's association_proxy), eliminate this column.
    entity_id : int
        This points back at the edit's annotation. I do not have a clue why I
        titled it entity_id. This seems like it could, and should, change. It
        used to be called the pointer_id. I guess entity_id is a step up from
        that? I'll make it annotation_id after I finish documenting this and
        working through other problems.
    first_line_num : int
        This corresponds to the :class:`Line` `num` that corresponds to the
        first line of the target of the annotation's current version, *not* it's
        id. This is because I do not want the annotation to point to an abstract
        id, but to a line in a book. Because I absolutely do not want to make
        this fragile.  I want a robust ability to export the annotations. This
        may be silly, and eventually someone can convince me it is, especially
        given association_proxies, etc. But for now it's staying like this.
    last_line_num : int
        The same as the first_line_num, but the last of the target.
    first_char_idx : int
        The string-index of the first character of the first line which
        corresponds to the character-by-character target of the annotation. I am
        not currently storing anything but 0 here. Once we write the JavaScript
        corresponding to char-by-char annotation target selection, this will
        change.

        Note: this method seems fragile to me, and I am nervous about it. If I
        ever begin to edit lines, these could become de-indexed improperly. Then
        we could get out-of-bounds exceptions all over the place and fail to
        render pages. I am interested in a more robust solution to this.
    last_char_idx : int
        The *last* character of the last line of the target of the annotation.
        Read first_char_idx for an explanation.

        Note: I would like for this to always be a negative number. This could
        *also* result in problems. But I feel like it would be better to reverse
        index the last character than to forward index the last character. It
        *feels* more robust.
    edition : :class:`Edition`
        The edition object the annotation is applied to. This will become an
        association_proxy when I get off my fat behind and take care of that.
        Probably pretty soon.
    annotation : :class:`Annotation`
        The annotation the edit is applied to.
    lines : list
        A list of all of the lines that are the target of the edit.
    context : list
        A list of all the lines that are the target of the edit *plus* five
        lines on either side of the first and last lines of the target lines.
    """
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    entity_id = db.Column(db.Integer,
                          db.ForeignKey('annotation.id', ondelete='CASCADE'),
                          index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    first_line_num = db.Column(db.Integer, db.ForeignKey('line.num'))
    last_line_num = db.Column(db.Integer, db.ForeignKey('line.num'), index=True)
    first_char_idx = db.Column(db.Integer)
    last_char_idx = db.Column(db.Integer)

    edition = db.relationship('Edition')

    annotation = db.relationship('Annotation')
    tags = db.relationship('Tag', secondary='tags', passive_deletes=True)
    lines = db.relationship(
        'Line', primaryjoin='and_(Line.num>=Edit.first_line_num,'
        'Line.num<=Edit.last_line_num, Line.edition_id==Edit.edition_id)',
        uselist=True, foreign_keys=[edition_id, first_line_num, last_line_num])
    context = db.relationship(
        'Line', primaryjoin='and_(Line.num>=Edit.first_line_num-5,'
        'Line.num<=Edit.last_line_num+5, Line.edition_id==Edit.edition_id)',
        uselist=True, viewonly=True,
        foreign_keys=[edition_id, first_line_num, last_line_num])

    @orm.reconstructor
    def init_on_load(self):
        """Create the hash_id that recognizes when an edit differs from it's
        previous version to prevent dupe edits.
        """
        s = (f'{self.first_line_num},{self.last_line_num},'
             f'{self.first_char_idx},{self.last_char_idx},'
             f'{self.body},{self.tags}')
        self.hash_id = sha1(s.encode('utf8')).hexdigest()

    def __init__(self, *args, **kwargs):
        """This init checks to see if the first line and last line aren't
        reversed, because that can be a problem. I should probably make it do
        the same for the characters.

        It also generates the hash_id to check against the previous edit.
        """
        super().__init__(*args, **kwargs)
        if self.first_line_num > self.last_line_num:
            tmp = self.last_line_num
            self.last_line_num = self.first_line_num
            self.first_line_num = tmp
        s = (f'{self.first_line_num},{self.last_line_num},'
             f'{self.first_char_idx},{self.last_char_idx},'
             f'{self.body},{self.tags}')
        self.hash_id = sha1(s.encode('utf8')).hexdigest()

    def __repr__(self):
        prefix = super().__repr__()
        return f"<{prefix} {self.annotation}>"

    def get_hl(self):
        """This method is supposed to return the specific lines of the target
        *and* truncate the first and last line based on the actual
        character-by-character targetting which is not in effect yet. It is,
        therefore, currently useless.
        """
        lines = self.lines
        if self.first_line_num == self.last_line_num:
            lines[0].line = lines[0].line[
                self.first_char_idx:self.last_char_idx]
        else:
            lines[0].line = lines[0].line[self.first_char_idx:]
            lines[-1].line = lines[-1].line[:self.last_char_idx]
        return lines


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
classes['AnnotationFlagEnum'] = AnnotationFlag.enum_cls
