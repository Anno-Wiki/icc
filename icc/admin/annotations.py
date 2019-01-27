from flask import render_template, flash, redirect, url_for, request,\
    current_app
from flask_login import current_user, login_required

from icc import db
from icc.forms import AreYouSureForm
from icc.funky import generate_next, authorize
from icc.admin import admin

from icc.models.annotation import (Annotation, Edit, AnnotationFlagEnum,
                                   AnnotationFlag)
from icc.models.content import Text, Edition
from icc.models.user import User


@admin.route('/deactivate/annotation/<annotation_id>/')
@login_required
@authorize('deactivate_annotations')
def deactivate(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotation.active = not annotation.active
    db.session.commit()
    if annotation.active:
        flash(f"Annotation {annotation.id} activated")
    else:
        flash(f"Annotation {annotation.id} deactivated.")

    redirect_url = generate_next(url_for('annotation',
                                         annotation_id=annotation_id))
    return redirect(redirect_url)


@admin.route('/list/deactivated/annotations/')
@login_required
@authorize('view_deactivated_annotations')
def view_deactivated_annotations():
    sort = request.args.get('sort', 'added', type=str)
    page = request.args.get('page', 1, type=int)
    if sort == 'added':
        annotations = Annotation.query.filter_by(active=False)\
            .order_by(Annotation.timestamp.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    elif sort == 'weight':
        annotations = Annotation.query.filter_by(active=False)\
            .order_by(Annotation.weight.desc())\
            .paginate(page, current_app.config['ANNOTATIONS_PER_PAGE'], False)
    sorts = {
        'added': url_for('admin.view_deactivated_annotations', page=page,
                         sort='added'),
        'weight': url_for('admin.view_deactivated_annotations', page=page,
                          sort='weight')
    }
    next_page = url_for(
        'admin.view_deactivated_annotations', page=annotations.next_num,
        sort=sort) if annotations.has_next else None
    prev_page = url_for(
        'admin.view_deactivated_annotations', page=annotations.prev_num,
        sort=sort) if annotations.has_prev else None

    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
        else None
    return render_template(
        'indexes/annotation_list.html', title="Deactivated Annotations",
        prev_page=prev_page, next_page=next_page, sort=sort, sorts=sorts,
        uservotes=uservotes, annotations=annotations.items)


@admin.route('/flags/annotation/all/')
@login_required
@authorize('resolve_annotation_flags')
def all_annotation_flags():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'marked', type=str)

    if sort == 'marked':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'marked_invert':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag':
        flags = AnnotationFlag.query\
            .outerjoin(AnnotationFlagEnum)\
            .order_by(AnnotationFlagEnum.flag.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag_invert':
        flags = AnnotationFlag.query\
            .outerjoin(AnnotationFlagEnum)\
            .order_by(AnnotationFlagEnum.flag.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_thrown.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_thrown.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower':
        flags = AnnotationFlag.query\
            .outerjoin(User, User.id == AnnotationFlag.thrower_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower_invert':
        flags = AnnotationFlag.query\
            .outerjoin(User, User.id == AnnotationFlag.thrower_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver':
        flags = AnnotationFlag.query\
            .outerjoin(User, User.id == AnnotationFlag.resolver_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver_invert':
        flags = AnnotationFlag.query\
            .outerjoin(User, User.id == AnnotationFlag.resolver_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved_invert':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'annotation':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.annotation_id.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'annotation_invert':
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.annotation_id.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'text':
        flags = AnnotationFlag.query\
            .join(Annotation, Annotation.id == AnnotationFlag.annotation_id)\
            .join(Edition, Edition.id == Annotation.edition_id)\
            .join(Text, Text.id == Edition.text_id)\
            .order_by(Text.sort_title)\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        flags = AnnotationFlag.query\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)

    sorts = {
        'marked': url_for('admin.all_annotation_flags', sort='marked',
                          page=page),
        'marked_invert': url_for('admin.all_annotation_flags',
                                 sort='marked_invert', page=page),
        'flag': url_for('admin.all_annotation_flags', sort='flag', page=page),
        'flag_invert': url_for('admin.all_annotation_flags', sort='flag_invert',
                               page=page),
        'time': url_for('admin.all_annotation_flags', sort='time', page=page),
        'time_invert': url_for('admin.all_annotation_flags', sort='time_invert',
                               page=page),
        'thrower': url_for('admin.all_annotation_flags', sort='thrower',
                           page=page),
        'thrower_invert': url_for('admin.all_annotation_flags',
                                  sort='thrower_invert', page=page),
        'resolver': url_for('admin.all_annotation_flags', sort='resolver',
                            page=page),
        'resolver_invert': url_for('admin.all_annotation_flags',
                                   sort='resolver_invert', page=page),
        'time_resolved': url_for('admin.all_annotation_flags',
                                 sort='time_resolved', page=page),
        'time_resolved_invert': url_for( 'admin.all_annotation_flags',
                                        sort='time_resolved_invert', page=page),
        'annotation': url_for( 'admin.all_annotation_flags', sort='annotation',
                              page=page),
        'annotation_invert': url_for('admin.all_annotation_flags',
                                     sort='annotation_invert', page=page),
        'text': url_for('admin.all_annotation_flags', sort='text', page=page),
        'text_invert': url_for('admin.all_annotation_flags', sort='text_invert',
                               page=page),
    }

    next_page = url_for(
        'admin.all_annotation_flags', page=flags.next_num, sort=sort
    ) if flags.has_next else None

    prev_page = url_for(
        'admin.all_annotation_flags', page=flags.prev_num, sort=sort
    ) if flags.has_prev else None

    return render_template(
        'indexes/all_annotation_flags.html', title=f"Annotation Flags",
        next_page=next_page, prev_page=prev_page, sort=sort, sorts=sorts,
        flags=flags.items)


@admin.route('/flags/annotation/<annotation_id>/')
@login_required
@authorize('resolve_annotation_flags')
def annotation_flags(annotation_id):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'marked', type=str)
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('resolve_deactivated_annotation_flags')

    if sort == 'marked':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'marked_invert':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag':
        flags = annotation.flag_history\
            .outerjoin(AnnotationFlagEnum)\
            .order_by(AnnotationFlagEnum.flag.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'flag_invert':
        flags = annotation.flag_history\
            .outerjoin(AnnotationFlagEnum)\
            .order_by(AnnotationFlagEnum.flag.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_thrown.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_invert':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_thrown.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower':
        flags = annotation.flag_history\
            .outerjoin(User, User.id == AnnotationFlag.thrower_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'thrower_invert':
        flags = annotation.flag_history\
            .outerjoin(User, User.id == AnnotationFlag.thrower_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver':
        flags = annotation.flag_history\
            .outerjoin(User, User.id == AnnotationFlag.resolver_id)\
            .order_by(User.displayname.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'resolver_invert':
        flags = annotation.flag_history\
            .outerjoin(User, User.id == AnnotationFlag.resolver_id)\
            .order_by(User.displayname.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    elif sort == 'time_resolved_invert':
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_resolved.asc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)
    else:
        flags = annotation.flag_history\
            .order_by(AnnotationFlag.time_resolved.desc())\
            .paginate(page, current_app.config['NOTIFICATIONS_PER_PAGE'], False)

    sorts = {
        'marked': url_for('admin.annotation_flags', annotation_id=annotation.id,
                          sort='marked', page=page),
        'marked_invert': url_for('admin.annotation_flags',
                                 annotation_id=annotation.id,
                                 sort='marked_invert', page=page),
        'flag': url_for('admin.annotation_flags', annotation_id=annotation.id,
                        sort='flag', page=page),
        'flag_invert': url_for('admin.annotation_flags',
                               annotation_id=annotation.id, sort='flag_invert',
                               page=page),
        'time': url_for('admin.annotation_flags', annotation_id=annotation.id,
                        sort='time', page=page),
        'time_invert': url_for('admin.annotation_flags',
                               annotation_id=annotation.id, sort='time_invert',
                               page=page),
        'thrower': url_for('admin.annotation_flags',
                           annotation_id=annotation.id, sort='thrower',
                           page=page),
        'thrower_invert': url_for('admin.annotation_flags',
                                  annotation_id=annotation.id,
                                  sort='thrower_invert', page=page),
        'resolver': url_for('admin.annotation_flags',
                            annotation_id=annotation.id, sort='resolver',
                            page=page),
        'resolver_invert': url_for('admin.annotation_flags',
                                   annotation_id=annotation.id,
                                   sort='resolver_invert', page=page),
        'time_resolved': url_for('admin.annotation_flags',
                                 annotation_id=annotation.id,
                                 sort='time_resolved', page=page),
        'time_resolved_invert': url_for('admin.annotation_flags',
                                        annotation_id=annotation.id,
                                        sort='time_resolved_invert', page=page),
    }

    next_page = url_for(
        'admin.annotation_flags', annotation_id=annotation.id,
        page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for(
        'admin.annotation_flags', annotation_id=annotation.id,
        page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template(
        'indexes/annotation_flags.html',
        title=f"Annotation {annotation.id} flags", next_page=next_page,
        prev_page=prev_page, sort=sort, sorts=sorts, flags=flags.items,
        annotation=annotation)


@admin.route('/flags/annotation/mark/<flag_id>/')
@login_required
@authorize('resolve_annotation_flags')
def mark_annotation_flag(flag_id):
    flag = AnnotationFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for('admin.annotation_flags',
                                         annotation_id=flag.annotation_id))
    if flag.time_resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/flags/annotation/<annotation_id>/mark/all/')
@login_required
@authorize('resolve_annotation_flags')
def mark_annotation_flags(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('resolve_deactivated_annotation_flags')
    redirect_url = generate_next(url_for('admin.annotation_flags',
                                         annotation_id=annotation_id))
    for flag in annotation.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)


@admin.route('/annotation/<annotation_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('delete_annotations')
def delete_annotation(annotation_id):
    form = AreYouSureForm()
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = url_for('main.text_annotations',
                           text_url=annotation.text.url)
    if form.validate_on_submit():
        for e in annotation.all_edits:
            e.tags = []
        db.session.delete(annotation)
        db.session.commit()
        flash(f"Annotation [{annotation_id}] deleted.")
        return redirect(redirect_url)
    text = """
If you click submit the annotation, all of the edits to the annotation, all of
the votes to the edits, all of the votes to the annotation, and all of the
reputation changes based on the annotation, will be deleted permanently.

This is not something to take lightly. Unless there is illegal content
associated with the annotation, you really ought to simply deactivate it.
    """
    return render_template(
        'forms/delete_check.html', title=f"Delete [{annotation_id}]", form=form,
        text=text)


@admin.route('/edit/<edit_id>/delete/', methods=['GET', 'POST'])
@login_required
@authorize('delete_annotations')
def delete_edit(edit_id):
    form = AreYouSureForm()
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = url_for('edit_history', annotation_id=edit.annotation_id)
    if form.validate_on_submit():
        if edit.current:
            edit.previous.current = True
        else:
            for e in edit.annotation.all_edits.order_by(Edit.num.desc()).all():
                if e.num > edit.num:
                    e.num -= 1
        flash(f"Edit #{edit.num} of [{edit.annotation_id}] deleted.")
        db.session.delete(edit)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the edit, all of the votes for the edit, and all of the
reputation changes based on the edit being approved will be deleted. The edit
numbers of all the subsequent edits will be decremented by one. It will
therefore be as though the edit never even existed.

The only reason for this is if there is illegal content in the edit.
    """
    return render_template(
        'forms/delete_check.html',
        title=f"Delete edit #{edit.num} of [{edit.annotation_id}]", form=form,
        text=text)
