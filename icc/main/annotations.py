import re
import difflib

from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, abort,\
    current_app
from flask_login import current_user, login_required
from sqlalchemy import and_

from icc import db
from icc.main import main

from icc.models.annotation import (Annotation, Comment, Vote, Edit, EditVote,
                                   Tag, AnnotationFlagEnum)
from icc.models.content import Text, Edition, Line
from icc.models.user import User

from icc.forms import AnnotationForm, CommentForm
from icc.funky import generate_next, line_check


@main.route(
    '/annotate/<text_url>/<first_line>/<last_line>', methods=['GET', 'POST'],
    defaults={'edition_num': None})
@main.route(
    '/annotate/<text_url>/edition/<edition_num>/<first_line>/<last_line>',
    methods=['GET', 'POST'])
@login_required
def annotate(text_url, edition_num, first_line, last_line):
    if int(first_line) > int(last_line):
        tmp = first_line
        first_line = last_line
        last_line = tmp
    if int(first_line) < 1:
        first_line = 1
    if int(last_line) < 1:
        first_line = 1
        last_line = 1

    text = Text.query.filter_by(title=text_url.replace('_', ' ')).first_or_404()
    if edition_num:
        edition = Edition.query.\
            filter(Edition.text_id == text.id,
                   Edition.num == edition_num).first_or_404()
    else:
        edition = text.primary
    lines = edition.lines\
        .filter(Line.num >= first_line, Line.num <= last_line).all()
    context = edition.lines\
        .filter(Line.num >= int(first_line)-5,
                Line.num <= int(last_line)+5).all()
    form = AnnotationForm()

    if lines is None:
        abort(404)

    redirect_url = generate_next(lines[0].get_url())

    if form.validate_on_submit():
        # line number boiler plate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))

        # Process all the tags
        raw_tags = form.tags.data.split()
        tags = []
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                flash(f"tag {tag} does not exist.")
                return render_template(
                    'forms/annotation.html', title=text.title, form=form,
                    text=text, edition=edition, lines=lines, context=context)

        if len(tags) > 5:
            flash("There is a five tag limit.")
            return render_template(
                'forms/annotation.html', title=text.title, form=form, text=text,
                edition=edition, lines=lines, context=context)

        annotation = Annotation(
            edition=edition, annotator=current_user, fl=fl, ll=ll,
            fc=form.first_char_idx.data, lc=form.last_char_idx.data,
            body=form.annotation.data, tags=tags)

        db.session.add(annotation)
        db.session.commit()

        flash("Annotation Submitted")

        return redirect(redirect_url)
    else:
        form.first_line.data = first_line
        form.last_line.data = last_line
        form.first_char_idx.data = 0
        form.last_char_idx.data = -1

    return render_template(
        'forms/annotation.html', title=f"Annotating {text.title}", form=form,
        text=text, edition=edition, lines=lines, context=context)


@main.route('/annotation/<annotation_id>')
def annotation(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')

    annotationflags = AnnotationFlagEnum.query.all()

    return render_template(
        'view/annotation.html', title=f"Annotation [{annotation.id}]",
        annotation=annotation, annotationflags=annotationflags)


@main.route('/annotation/<annotation_id>/flag/<flag_id>')
@login_required
def flag_annotation(flag_id, annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)

    redirect_url = generate_next(url_for('main.annotation',
                                         annotation_id=annotation.id))

    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')
    flag = AnnotationFlagEnum.query.get_or_404(flag_id)

    annotation.flag(flag, current_user)
    db.session.commit()
    flash(f"Annotation {annotation.id} flagged \"{flag.flag}\"")
    return redirect(redirect_url)


# Voting routes
@main.route('/upvote/<annotation_id>')
@login_required
def upvote(annotation_id):
    redirect_url = generate_next(url_for('main.annotation',
                                         annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
        return redirect(redirect_url)

    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotations.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user.voteballots\
            .filter(Vote.annotation == annotation).first()
        diff = datetime.utcnow() - vote.timestamp

        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.upvote(current_user)
    db.session.commit()

    return redirect(redirect_url)


@main.route('/downvote/<annotation_id>')
@login_required
def downvote(annotation_id):
    redirect_url = generate_next(url_for('main.annotation',
                                         annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")

    if current_user == annotation.annotator:
        flash("You cannot vote on your own annotation.")
        return redirect(redirect_url)
    elif current_user.already_voted(annotation):
        vote = current_user\
            .voteballots.filter(Vote.annotation == annotation).first()
        diff = datetime.utcnow() - vote.timestamp

        if diff.days > 0 and annotation.HEAD.modified < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return redirect(redirect_url)
        elif not vote.is_up():
            annotation.rollback(vote)
            db.session.commit()
            return redirect(redirect_url)
        else:
            annotation.rollback(vote)

    annotation.downvote(current_user)
    db.session.commit()

    return redirect(redirect_url)


# Edit routes
@main.route('/edit/<annotation_id>', methods=['GET', 'POST'])
@login_required
def edit(annotation_id):
    form = AnnotationForm()
    redirect_url = generate_next(url_for('main.annotation',
                                         annotation_id=annotation_id))

    annotation = Annotation.query.get_or_404(annotation_id)
    if (annotation.locked and not
            current_user.is_authorized('edit_locked_annotations')):
        flash("That annotation is locked from editing.")
        return redirect(redirect_url)
    elif annotation.edit_pending:
        flash("There is an edit still pending peer review.")
        return redirect(redirect_url)
    elif not annotation.active:
        current_user.authorize('edit_deactivated_annotations')

    lines = annotation.HEAD.lines
    context = annotation.HEAD.context

    if form.validate_on_submit():
        # line number boilerplate
        fl, ll = line_check(int(form.first_line.data), int(form.last_line.data))
        fail = False    # if at any point we run into problems, flip this var

        raw_tags = form.tags.data.split()
        tags = []
        for tag in raw_tags:
            t = Tag.query.filter_by(tag=tag).first()
            if t:
                tags.append(t)
            else:
                fail = True
                flash(f"tag {tag} does not exist.")
        if len(tags) > 5:
            fail = True
            flash("There is a five tag limit.")

        success = annotation.edit(
            editor=current_user, reason=form.reason.data, fl=fl, ll=ll,
            fc=form.first_char_idx.data, lc=form.last_char_idx.data,
            body=form.annotation.data, tags=tags)

        # rerender the template with the work already filled
        if not success or fail:
            db.session.rollback()
            return render_template(
                'forms/annotation.html', form=form, title=annotation.text.title,
                lines=lines, text=annotation.text, annotation=annotation)
        db.session.commit()
        return redirect(redirect_url)

    elif not annotation.edit_pending:
        tag_strings = []
        for t in annotation.HEAD.tags:
            tag_strings.append(t.tag)
        form.first_line.data = annotation.HEAD.first_line_num
        form.last_line.data = annotation.HEAD.last_line_num
        form.first_char_idx.data = annotation.HEAD.first_char_idx
        form.last_char_idx.data = annotation.HEAD.last_char_idx
        form.annotation.data = annotation.HEAD.body
        form.tags.data = ' '.join(tag_strings)
    return render_template(
        'forms/annotation.html', title=f"Edit Annotation {annotation.id}",
        form=form,  text=annotation.text, lines=lines, annotation=annotation,
        context=context)


@main.route('/annotation/<annotation_id>/edit/history')
def edit_history(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize('view_deactivated_annotations')

    default = 'num'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'num_invert', type=str)

    e = Edit
    a = annotation
    sorts = {
        'num': a.history.order_by(e.num.asc()),
        'num_invert': a.history.order_by(e.num.desc()),
        'editor': a.history.join(User).order_by(User.displayname.asc()),
        'editor_invert': (a.history.join(User)
                          .order_by(User.displayname.desc())),
        'time': a.history.order_by(e.timestamp.asc()),
        'time_invert': a.history.order_by(e.timestamp.desc()),
        'reason': a.history.order_by(e.reason.asc()),
        'reason_invert': a.history.order_by(e.reason.desc()),
    }
    sort = sort if sort in sorts else default
    edits = sorts[sort].paginate(page,
                                 current_app.config['NOTIFICATIONS_PER_PAGE'],
                                 False)
    urlsorts = {
        key: url_for('main.edit_history', annotation_id=annotation_id,
                     page=edits.next_num, sort=key) for key in sorts.keys()
    }

    next_page = url_for(
        'main.edit_history', annotation_id=annotation_id, page=edits.next_num,
        sort=sort) if edits.has_next else None
    prev_page = url_for(
        'main.edit_history', annotation_id=annotation_id, page=edits.prev_num,
        sort=sort) if edits.has_prev else None

    return render_template('indexes/edit_history.html', title="Edit History",
                           next_page=next_page, prev_page=prev_page, page=page,
                           sort=sort, sorts=urlsorts,
                           edits=edits.items, annotation=annotation)


@main.route('/annotation/<annotation_id>/edit/<num>')
def view_edit(annotation_id, num):
    edit = Edit.query.filter(Edit.entity_id == annotation_id, Edit.num == num,
                             Edit.approved == True).first_or_404()
    if not edit.previous:
        return render_template(
            'view/first_version.html', title="First Version of "
            f"[{edit.annotation.id}]", edit=edit)

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.previous.body)
    diff2 = re.sub(r'(?<!\n)\r?\n(?![\r\n])', ' ', edit.body)
    diff = list(difflib.Differ().compare(diff1.splitlines(),
                                         diff2.splitlines()))

    tags = [tag for tag in edit.tags]
    for tag in edit.previous.tags:
        if tag not in tags:
            tags.append(tag)

    if edit.first_line_num > edit.previous.first_line_num:
        context = [line for line in edit.previous.context]
        for line in edit.context:
            if line not in context:
                context.append(line)
    else:
        context = [line for line in edit.context]
        for line in edit.previous.context:
            if line not in context:
                context.append(line)

    return render_template('view/edit.html', title=f"Edit number {edit.num}",
                           diff=diff, edit=edit, tags=tags, context=context)


# Comment routes
@main.route('/annotation/<annotation_id>/comments', methods=['GET', 'POST'])
def comments(annotation_id):
    page = request.args.get('page', 1, type=int)
    form = CommentForm()

    annotation = Annotation.query.get_or_404(annotation_id)
    comments = annotation.comments\
        .filter(Comment.depth == 0)\
        .paginate(page, current_app.config['COMMENTS_PER_PAGE'], False)

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You must be logged in to post a comment.")
            return redirect(url_for('main.comments',
                                    annotation_id=annotation.id))
        comment = Comment(annotation=annotation, body=form.comment.data,
                          poster=current_user)
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted")
        return redirect(url_for('main.comments', annotation_id=annotation.id))

    return render_template(
        'indexes/comments.html', title=f"[{annotation.id}] comments", form=form,
        annotation=annotation, comments=comments.items)


@main.route('/annotation/<annotation_id>/comment/<comment_id>/reply',
            methods=['GET', 'POST'])
@login_required
def reply(annotation_id, comment_id):
    form = CommentForm()

    annotation = Annotation.query.get_or_404(annotation_id)
    comment = Comment.query.get_or_404(comment_id)

    if form.validate_on_submit():
        reply = Comment(annotation=annotation, body=form.comment.data,
                        poster=current_user, parent=comment,
                        depth=comment.depth+1)
        db.session.add(reply)
        db.session.commit()
        flash("Reply posted")
        return redirect(url_for('main.comments', annotation_id=annotation.id))
    return render_template('forms/reply.html', title="Reply", form=form,
                           comment=comment)
