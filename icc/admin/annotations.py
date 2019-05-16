"""Administration routes for annotations."""

from flask import (render_template, flash, redirect, url_for, request,
                   current_app, abort)
from flask_login import current_user, login_required

from icc import db
from icc.forms import AreYouSureForm
from icc.funky import generate_next, authorize
from icc.admin import admin

from icc.models.annotation import Annotation, Edit, AnnotationFlag, Comment
from icc.models.content import Text, Edition
from icc.models.user import User


@admin.route('/annotation/<annotation_id>/deactivate')
@login_required
@authorize('deactivate_annotations')
def deactivate_annotation(annotation_id):
    """This route will deactivate (or reactivate) an annotation. Requires the
    'deactivate_annotations' right.
    """
    annotation = Annotation.query.get_or_404(annotation_id)
    annotation.active = not annotation.active
    db.session.commit()

    if annotation.active:
        flash(f"Annotation {annotation.id} reactivated")
    else:
        flash(f"Annotation {annotation.id} deactivated.")

    redirect_url = generate_next(url_for('main.annotation',
                                         annotation_id=annotation_id))
    return redirect(redirect_url)


@admin.route('/list/annotations/deactivated')
@login_required
@authorize('view_deactivated_annotations')
def view_deactivated_annotations():
    """View a list of all deactivated annotations. There should never be that
    many of these because we're going to make deletion a thing. I think. I need
    to overhaul annotation flagging with voting.
    """
    default = 'added'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'added': Annotation.query.order_by(Annotation.timestamp.desc()),
        'weight': Annotation.query.order_by(Annotation.weight.desc()),
    }

    sort = sort if sort in sorts else default
    annotations = sorts[sort].filter_by(active=False)\
        .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    if not annotations.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.view_deactivated_annotations', sort=key) for
                key in sorts.keys()}
    next_page = (url_for('admin.view_deactivated_annotations',
                         page=annotations.next_num, sort=sort) if
                 annotations.has_next else None)
    prev_page = (url_for('admin.view_deactivated_annotations',
                         page=annotations.prev_num, sort=sort) if
                 annotations.has_prev else None)
    return render_template('indexes/annotation_list.html',
                           title="Deactivated Annotations",
                           prev_page=prev_page, next_page=next_page,
                           sort=sort, sorts=sorturls,
                           annotations=annotations.items)


@admin.route('/flags/annotation/all/')
@login_required
@authorize('resolve_annotation_flags')
def all_annotation_flags():
    """View all the flags on all annotations. This is a high-level admin route
    for now. But soon I will make this a more democratic process including with
    voting.
    """
    default = 'flag'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    sorts = {
        'flag': (AnnotationFlag.query.outerjoin(AnnotationFlag.enum_cls)
                 .order_by(AnnotationFlag.enum_cls.enum.asc())),
        'thrower': (AnnotationFlag.query
                    .join(User, User.id==AnnotationFlag.thrower_id)
                    .order_by(User.displayname.asc())),
        'time': (AnnotationFlag.query
                 .order_by(AnnotationFlag.time_thrown.desc())),
        'annotation': (AnnotationFlag.query
                       .order_by(AnnotationFlag.annotation_id.asc())),
        'text': (AnnotationFlag.query
                 .join(Annotation, Annotation.id==AnnotationFlag.annotation_id)
                 .join(Edition, Edition.id==Annotation.edition_id)
                 .join(Text, Text.id==Edition.text_id)
                 .order_by(Text.sort_title.asc())),
    }

    sort = sort if sort in sorts else default
    flags = sorts[sort].filter(AnnotationFlag.time_resolved==None).paginate(page,
                                 current_app.config['NOTIFICATIONS_PER_PAGE'],
                                 False)
    if not flags.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.all_annotation_flags', sort=key) for key in
                sorts.keys()}
    next_page = url_for('admin.all_annotation_flags', page=flags.next_num,
                        sort=sort) if flags.has_next else None
    prev_page = url_for('admin.all_annotation_flags', page=flags.prev_num,
                        sort=sort) if flags.has_prev else None
    return render_template('indexes/all_annotation_flags.html',
                           title=f"Annotation Flags",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           flags=flags.items)


@admin.route('/flags/annotation/<annotation_id>/')
@login_required
@authorize('resolve_annotation_flags')
def annotation_flags(annotation_id):
    """View all flags for a given annotation."""
    default = 'unresolved'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', default, type=str)

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('resolve_deactivated_annotation_flags')

    sorts = {
        'unresolved': (annotation.flags
                       .order_by(AnnotationFlag.time_resolved.asc())),
        'flag': (annotation.flags.outerjoin(AnnotationFlag.enum_cls)
                 .order_by(AnnotationFlag.enum_cls.enum.asc())),
        'time-thrown': (annotation.flags
                        .order_by(AnnotationFlag.time_thrown.desc())),
        'time-resolved': (annotation.flags
                          .order_by(AnnotationFlag.time_resolved.desc())),
    }

    sort = sort if sort in sorts else default
    flags = sorts[sort].paginate(page,
                                 current_app.config['NOTIFICATIONS_PER_PAGE'],
                                 False)
    if not flags.items and page > 1:
        abort(404)

    sorturls = {key: url_for('admin.annotation_flags',
                             annotation_id=annotation_id, sort=key) for key in
                sorts.keys()}
    next_page = (url_for('admin.annotation_flags', annotation_id=annotation.id,
                         page=flags.next_num, sort=sort) if flags.has_next else
                 None)
    prev_page = (url_for('admin.annotation_flags', annotation_id=annotation.id,
                         page=flags.prev_num, sort=sort) if flags.has_prev else
                 None)
    return render_template('indexes/annotation_flags.html',
                           title=f"Annotation {annotation.id} flags",
                           next_page=next_page, prev_page=prev_page,
                           sort=sort, sorts=sorturls,
                           flags=flags.items, annotation=annotation)


@admin.route('/flags/annotation/mark/<flag_id>/')
@login_required
@authorize('resolve_annotation_flags')
def mark_annotation_flag(flag_id):
    """Resolve/Unresolve an annotation flag. This system needs to be overhauled.
    """
    flag = AnnotationFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for('admin.annotation_flags',
                                         annotation_id=flag.annotation_id))
    if flag.time_resolved:
        flag.unresolve()
        flash(f"Flag {flag.enum.enum} on annotation [{flag.entity.id}] marked "
              "unresolved.")
    else:
        flag.resolve(current_user)
        flash(f"Flag {flag.enum.enum} on annotation [{flag.entity.id}] marked "
              "resolved.")
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/flags/annotation/<annotation_id>/mark/all/')
@login_required
@authorize('resolve_annotation_flags')
def mark_all_annotation_flags(annotation_id):
    """Resolve all flags for a given annotation. This route will be deprecated
    after the annotation flag democratization overhaul."""
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('resolve_deactivated_annotation_flags')
    redirect_url = generate_next(url_for('admin.annotation_flags',
                                         annotation_id=annotation_id))
    for flag in annotation.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    flash("All flags marked resolved.")
    return redirect(redirect_url)


@admin.route('/annotation/<annotation_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('delete_annotations')
def delete_annotation(annotation_id):
    """Delete an annotation. Like, full on remove it from the system.

    This route will be eliminated. Or it's security priveleges changed. The
    purpose of this route is for two different scenarios:

    1. The annotation is useless/spam/etc. and should be eliminated.
    2. The annotation is dangerous (illegal content, copyright violation, etc.)

    My inclination is to keep it for the latter, but use other methods for the
    former.
    """
    form = AreYouSureForm()
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = generate_next(url_for('main.text_annotations',
                                         text_url=annotation.text.url))
    if form.validate_on_submit():
        for e in annotation.all_edits:
            e.tags = []
        db.session.delete(annotation)
        db.session.commit()
        flash(f"Annotation [{annotation_id}] deleted.")
        return redirect(redirect_url)
    text = """If you click submit the annotation, all of the edits to the
    annotation, all of the votes to the edits, all of the votes to the
    annotation, and all of the reputation changes based on the annotation, will
    be deleted permanently.

    This is not something to take lightly. Unless there is illegal content
    associated with the annotation, you really ought to simply deactivate it.
    """
    return render_template('forms/delete_check.html',
                           title=f"Delete [{annotation_id}]",
                           form=form,
                           text=text)

@admin.route('/annotation/<annotation_id>/comment/<comment_id>', methods=['GET',
                                                                          'POST'])
@login_required
@authorize('delete_comments')
def delete_comment(annotation_id, comment_id):
    """Delete a comment."""
    form = AreYouSureForm()
    comment = Comment.query.get_or_404(comment_id)
    redirect_url = generate_next(comment.url)

    if form.validate_on_submit():
        comment.body = "[deleted]"
        db.session.commit()
        flash(f"Comment deleted.")
        return redirect(redirect_url)
    text = """This is to delete a comment. The only reason to delete a comment
is if it is illegal content.

It doesn't actually "delete" the comment, it just obliterates the content.
    """
    return render_template('forms/delete_check.html',
                           title=f"Delete Comment {comment_id}",
                           form=form, text=text)
