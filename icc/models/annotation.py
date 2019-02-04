import sys
import inspect
from datetime import datetime
from hashlib import sha1

from sqlalchemy import orm
from sqlalchemy.orm import backref
from flask import url_for, flash, current_app as app

from icc import db
from icc.models.mixins import Base, VoteMixin, EditMixin, EnumMixin
from icc.models.user import ReputationEnum, ReputationChange
from icc.models.wiki import Wiki


class Tag(Base):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(128), index=True, unique=True)
    locked = db.Column(db.Boolean, default=False)
    wiki_id = db.Column(db.Integer, db.ForeignKey('wiki.id'), nullable=False)

    wiki = db.relationship('Wiki', backref=backref('tag', uselist=False))
    annotations = db.relationship(
        'Annotation', secondary='join(tags, Edit, and_(tags.c.edit_id==Edit.id,'
        'Edit.current==True))', primaryjoin='Tag.id==tags.c.tag_id',
        secondaryjoin='and_(Edit.entity_id==Annotation.id,'
        'Annotation.active==True)', lazy='dynamic', passive_deletes=True)

    def __init__(self, *args, **kwargs):
        description = kwargs.pop('description', None)
        description = 'This tag has no description yet.' if not description\
            else description
        super().__init__(*args, **kwargs)
        self.wiki = Wiki(body=description, entity_string=str(self))

    def __repr__(self):
        return f'<Tag {self.id}: {self.tag}>'

    def __str__(self):
        return f'<tag>{self.tag}</tag>'

    @classmethod
    def intersect(cls, tags):
        """Return a base query that is the intersection of all annotations for a
        tuple of tags.
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
        """Return a base query that is the intersection of all annotations for a
        tuple of tags.
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

    def get_url(self):
        return url_for('main.tag', tag=self.tag)


class Comment(Base):
    id = db.Column(db.Integer, primary_key=True)
    poster_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    annotation_id = db.Column(
        db.Integer, db.ForeignKey('annotation.id', ondelete='CASCADE'),
        index=True, nullable=False)
    parent_id = db.Column(
        db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), index=True,
        default=None)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    weight = db.Column(db.Integer, default=0)
    depth = db.Column(db.Integer, default=0)
    body = db.Column(db.Text)

    poster = db.relationship('User', backref=backref('comments',
                                                     lazy='dynamic'))
    annotation = db.relationship(
        'Annotation', backref=backref('comments', lazy='dynamic',
                                      passive_deletes=True))
    parent = db.relationship('Comment', remote_side=[id],
                             backref=backref('children', lazy='dynamic'))

    def __repr__(self):
            return f'<Comment {self.parent_id} on [{self.annotation_id}]>'


class Vote(Base, VoteMixin):
    id = db.Column(db.Integer, primary_key=True)
    annotation_id = db.Column(db.Integer,
                              db.ForeignKey('annotation.id',
                                            ondelete='CASCADE'), index=True)
    annotation = db.relationship('Annotation',
                                 backref=backref('ballots', lazy='dynamic'))

    reputation_change_id = db.Column(db.Integer,
                                     db.ForeignKey('reputation_change.id',
                                                   ondelete='CASCADE'))
    repchange = db.relationship('ReputationChange',
                                backref=backref('vote', uselist=False))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.annotation}"


class AnnotationFlagEnum(Base, EnumMixin):
    id = db.Column(db.Integer, primary_key=True)


class AnnotationFlag(Base):
    id = db.Column(db.Integer, primary_key=True)
    annotation_flag_id = db.Column(db.Integer,
                                   db.ForeignKey('annotation_flag_enum.id'),
                                   index=True)
    annotation_id = db.Column(
        db.Integer, db.ForeignKey('annotation.id', ondelete='CASCADE'),
        index=True)

    thrower_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    time_thrown = db.Column(db.DateTime, default=datetime.utcnow())

    time_resolved = db.Column(db.DateTime)
    resolver_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    annotation = db.relationship('Annotation', foreign_keys=[annotation_id])
    thrower = db.relationship('User', foreign_keys=[thrower_id])
    resolver = db.relationship('User', foreign_keys=[resolver_id])
    flag = db.relationship('AnnotationFlagEnum')

    def __repr__(self):
        if self.resolver:
            return f'<X AnnotationFlag: {self.flag.flag} at {self.time_thrown}>'
        else:
            return (f'<AnnotationFlag thrown: {self.flag.flag} at'
                    f' {self.time_thrown}>')

    def resolve(self, resolver):
        self.time_resolved = datetime.utcnow()
        self.resolver = resolver

    def unresolve(self):
        self.time_resolved = None
        self.resolver = None


class Annotation(Base):
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    weight = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    locked = db.Column(db.Boolean, index=True, default=False)
    active = db.Column(db.Boolean, default=True)

    annotator = db.relationship('User', backref=backref('annotations',
                                                        lazy='dynamic'))
    first_line = db.relationship(
        'Line', secondary='edit', primaryjoin='Edit.entity_id==Annotation.id',
        secondaryjoin='and_(Line.edition_id==Annotation.edition_id,'
        'Edit.first_line_num==Line.num)', uselist=False)

    edition = db.relationship('Edition', backref=backref('annotations',
                                                         lazy='dynamic'))
    text = db.relationship('Text', secondary='edition',
                           backref=backref('annotations', lazy='dynamic'),
                           uselist=False)

    # relationships to `Edit`
    HEAD = db.relationship('Edit', primaryjoin='and_(Edit.current==True,'
                           'Edit.entity_id==Annotation.id)', uselist=False)

    edits = db.relationship(
        'Edit', primaryjoin='and_(Edit.entity_id==Annotation.id,'
        'Edit.approved==True)', passive_deletes=True)
    history = db.relationship(
        'Edit', primaryjoin='and_(Edit.entity_id==Annotation.id,'
        'Edit.approved==True)', lazy='dynamic', passive_deletes=True)
    all_edits = db.relationship(
        'Edit', primaryjoin='Edit.entity_id==Annotation.id', lazy='dynamic',
        passive_deletes=True)
    edit_pending = db.relationship(
        'Edit', primaryjoin='and_(Edit.entity_id==Annotation.id,'
        'Edit.approved==False, Edit.rejected==False)', passive_deletes=True)

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

    def __init__(self, *ignore, edition, annotator, locked=False, fl, ll, fc,
                 lc, body, tags):
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
        params = [editor, reason, fl, ll, fc, lc, body, tags]
        if ignore:
            raise TypeError("Positional arguments not accepted.")
        elif None in params:
            raise TypeError("Keyword arguments cannot be None.")
        elif not type(tags) == list:
            raise TypeError("Tags must be a list of tags.")
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

    def upvote(self, voter):
        reptype = user.ReputationEnum.query.filter_by(enum='upvote').first()
        weight = voter.up_power()
        repchange = user.ReputationChange(user=self.annotator, type=reptype,
                                     delta=reptype.default_delta)
        vote = Vote(voter=voter, annotation=self, delta=weight,
                    repchange=repchange)
        self.annotator.reputation += repchange.delta
        self.weight += vote.delta
        db.session.add(vote)

    def downvote(self, voter):
        reptype = user.ReputationEnum.query.filter_by(enum='downvote').first()
        weight = voter.down_power()
        if self.annotator.reputation + reptype.default_delta < 0:
            repdelta = -self.annotator.reputation
        else:
            repdelta = reptype.default_delta
        repchange = user.ReputationChange(user=self.annotator, type=reptype,
                                     delta=repdelta)
        vote = Vote(voter=voter, annotation=self, delta=weight,
                    repchange=repchange)
        self.weight += vote.delta
        self.annotator.reputation += repchange.delta
        db.session.add(vote)

    def rollback(self, vote):
        self.weight -= vote.delta
        if self.annotator.reputation - vote.repchange.delta < 0:
            delta = -self.annotator.reputation
        else:
            delta = vote.repchange.delta
        self.annotator.reputation -= delta
        db.session.delete(vote)
        db.session.delete(vote.repchange)

    def flag(self, flag, thrower):
        event = AnnotationFlag(flag=flag, annotation=self, thrower=thrower)
        db.session.add(event)

    def readable_weight(self):
        if self.weight >= 1000000 or self.weight <= -1000000:
            return f'{round(self.weight/1000000,1)}m'
        elif self.weight >= 1000 or self.weight <= -1000:
            return f'{round(self.weight/1000,1)}k'
        else:
            return f'{self.weight}'


class EditVote(Base, VoteMixin):
    id = db.Column(db.Integer, primary_key=True)
    edit_id = db.Column(
        db.Integer, db.ForeignKey('edit.id', ondelete='CASCADE'), index=True)
    edit = db.relationship('Edit',
                           backref=backref('edit_ballots', lazy='dynamic',
                                           passive_deletes=True))
    reputation_change_id = db.Column(
        db.Integer, db.ForeignKey('reputation_change.id'), default=None)
    repchange = db.relationship(
        'ReputationChange', backref=backref('edit_vote', uselist=False))

    def __repr__(self):
        prefix = super().__repr__()
        return f"{prefix}{self.edit}"


class Edit(Base, EditMixin):
    id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'), index=True)
    entity_id = db.Column(db.Integer,
                          db.ForeignKey('annotation.id', ondelete='CASCADE'),
                          index=True)

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
        s = (f'{self.first_line_num},{self.last_line_num},'
             f'{self.first_char_idx},{self.last_char_idx},'
             f'{self.body},{self.tags}')
        self.hash_id = sha1(s.encode('utf8')).hexdigest()

    def __init__(self, *args, **kwargs):
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
        return f"{prefix}    {self.annotation}>"

    def get_hl(self):
        lines = self.lines
        if self.first_line_num == self.last_line_num:
            lines[0].line = lines[0].line[
                self.first_char_idx:self.last_char_idx]
        else:
            lines[0].line = lines[0].line[self.first_char_idx:]
            lines[-1].line = lines[-1].line[:self.last_char_idx]
        return lines

    def upvote(self, voter):
        if self.approved or self.rejected:
            flash("That edit is no longer pending.")
            return
        if self.editor == voter:
            flash("You cannot vote on your own edits.")
            return
        ov = voter.get_edit_vote(self)
        if ov:
            if ov.is_up():
                self.rollback(ov)
                return
            else:
                self.rollback(ov)
        vote = EditVote(edit=self, delta=1, voter=voter)
        self.weight += vote.delta
        db.session.add(vote)
        if self.weight >= app.config['VOTES_FOR_EDIT_APPROVAL'] or\
                voter.is_authorized('immediate_edits'):
            self.approve()

    def downvote(self, voter):
        if self.approved or self.rejected:
            flash("That edit is no longer pending.")
            return
        if self.editor == voter:
            flash("You cannot vote on your own edits.")
            return
        ov = voter.get_edit_vote(self)
        if ov:
            if not ov.is_up():
                self.rollback(ov)
                return
            else:
                self.rollback(ov)
        vote = EditVote(edit=self, delta=-1, voter=voter)
        self.weight += vote.delta
        db.session.add(vote)
        if self.weight <= app.config['VOTES_FOR_EDIT_REJECTION'] or\
                voter.is_authorized('immediate_edits'):
            self.reject()

    def approve(self):
        self.approved = True
        self.annotation.HEAD.current = False
        self.current = True
        flash("The edit was approved.")


classes = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
