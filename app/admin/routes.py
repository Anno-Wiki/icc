import re, difflib

from flask import render_template, flash, redirect, url_for, request, abort,\
        Blueprint
from flask_login import current_user, login_required
from sqlalchemy import and_

from app import app, db
from app.funky import generate_next, authorize
from app.forms import AreYouSureForm
from app.models import User, UserFlag, UserFlagEnum,\
        Line, Text, TextRequest, Edition, Writer, Tag, TagRequest,\
        Annotation, AnnotationFlag, AnnotationFlagEnum, Edit, EditVote,\
        WikiEdit, Wiki, WikiEditVote

from app.admin import admin
from app.admin.forms import TagForm, LineForm

#################
## User Routes ##
#################

@admin.route("/user/<user_id>/delete/", methods=["GET", "POST"])
@login_required
@authorize("anonymize_users")
def anonymize_user(user_id):
    form = AreYouSureForm()
    user = User.query.get_or_404(user_id)
    redirect_url = url_for("user", user_id=user.id)
    if form.validate_on_submit():
        user.displayname = f"x_user{user.id}"
        user.email = f"{user.id}"
        user.password_hash = "***"
        user.about_me = ""
        db.session.commit()
        flash("Account anonymized.")
        return redirect(redirect_url)

    text = f"""
If you click submit you will forcibly anonymize this user ({user.displayname}).
    """
    return render_template("forms/delete_check.html", form=form,
            title="Are you sure?", text=text)

@admin.route("/lock/user/<user_id>/")
@login_required
@authorize("lock_users")
def lock_user(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for("user", user_id=user.id))
    user.locked = not user.locked
    db.session.commit()
    flash(f"User account {user.displayname} locked.")
    return redirect(redirect_url)

################
## User Flags ##
################

@admin.route("/flags/user/all/")
@login_required
@authorize("resolve_user_flags")
def all_user_flags():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)

    if sort == "marked":
        flags = UserFlag.query\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = UserFlag.query\
                .order_by(UserFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag":
        flags = UserFlag.query\
                .outerjoin(UserFlagEnum)\
                .order_by(UserFlagEnum.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = UserFlag.query\
                .outerjoin(UserFlagEnum)\
                .order_by(UserFlagEnum.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        flags = UserFlag.query\
                .order_by(UserFlag.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = UserFlag.query\
                .order_by(UserFlag.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.resolver_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.resolver_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved":
        flags = UserFlag.query\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved_invert":
        flags = UserFlag.query\
                .order_by(UserFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "user":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.user_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "user_invert":
        flags = UserFlag.query\
                .outerjoin(User, User.id==UserFlag.user_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        flags = UserFlag.query\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("admin.all_user_flags", sort="marked", page=page),
            "marked_invert": url_for("admin.all_user_flags", sort="marked_invert", page=page),
            "flag": url_for("admin.all_user_flags", sort="flag", page=page),
            "flag_invert": url_for("admin.all_user_flags", sort="flag_invert", page=page),
            "time": url_for("admin.all_user_flags", sort="time", page=page),
            "time_invert": url_for("admin.all_user_flags", sort="time_invert", page=page),
            "thrower": url_for("admin.all_user_flags", sort="thrower", page=page),
            "thrower_invert": url_for("admin.all_user_flags", sort="thrower_invert", page=page),
            "resolver": url_for("admin.all_user_flags", sort="resolver", page=page),
            "resolver_invert": url_for("admin.all_user_flags", sort="resolver_invert", page=page),
            "time_resolved": url_for("admin.all_user_flags", sort="time_resolved", page=page),
            "time_resolved_invert": url_for("admin.all_user_flags", sort="time_resolved_invert", page=page),
            "user": url_for("admin.all_user_flags", sort="user", page=page),
            "user_invert": url_for("admin.all_user_flags", sort="user_invert", page=page),
            }

    next_page = url_for("admin.all_user_flags", page=flags.next_num, sort=sort)\
            if flags.has_next else None
    prev_page = url_for("admin.all_user_flags", page=flags.prev_num, sort=sort)\
            if flags.has_prev else None
    return render_template("indexes/all_user_flags.html",
            title=f"User Flags", flags=flags.items, sort=sort, sorts=sorts,
            next_page=next_page, prev_page=prev_page)

# user flags
@admin.route("/flags/user/<user_id>/")
@login_required
@authorize("resolve_user_flags")
def user_flags(user_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    user = User.query.get_or_404(user_id)
    if sort == "marked":
        flags = user.flag_history\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = user.flag_history\
                .order_by(UserFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag":
        flags = user.flag_history\
                .outerjoin(UserFlagEnum)\
                .order_by(UserFlagEnum.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = user.flag_history\
                .outerjoin(UserFlagEnum)\
                .order_by(UserFlagEnum.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        flags = user.flag_history\
                .order_by(UserFlag.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = user.flag_history\
                .order_by(UserFlag.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlag.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlag.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlag.resolver_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = user.flag_history\
                .outerjoin(User, User.id==UserFlag.resolver_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved":
        flags = user.flag_history\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved_invert":
        flags = user.flag_history\
                .order_by(UserFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    else:
        flags = user.flag_history\
                .order_by(UserFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("admin.user_flags", user_id=user.id, sort="marked", page=page),
            "marked_invert": url_for("admin.user_flags", user_id=user.id, sort="marked_invert", page=page),
            "flag": url_for("admin.user_flags", user_id=user.id, sort="flag", page=page),
            "flag_invert": url_for("admin.user_flags", user_id=user.id, sort="flag_invert", page=page),
            "time": url_for("admin.user_flags", user_id=user.id, sort="time", page=page),
            "time_invert": url_for("admin.user_flags", user_id=user.id, sort="time_invert", page=page),
            "thrower": url_for("admin.user_flags", user_id=user.id, sort="thrower", page=page),
            "thrower_invert": url_for("admin.user_flags", user_id=user.id, sort="thrower_invert", page=page),
            "resolver": url_for("admin.user_flags", user_id=user.id, sort="resolver", page=page),
            "resolver_invert": url_for("admin.user_flags", user_id=user.id, sort="resolver_invert", page=page),
            "time_resolved": url_for("admin.user_flags", user_id=user.id, sort="time_resolved", page=page),
            "time_resolved_invert": url_for("admin.user_flags", user_id=user.id, sort="time_resolved_invert", page=page),
            }

    next_page = url_for("admin.user_flags", user_id=user.id, page=flags.next_num,
            sort=sort) if flags.has_next else None
    prev_page = url_for("admin.user_flags", user_id=user.id, page=flags.prev_num,
            sort=sort) if flags.has_prev else None
    return render_template("indexes/user_flags.html",
            title=f"{user.displayname} flags", user=user, flags=flags.items,
            sort=sort, sorts=sorts, next_page=next_page, prev_page=prev_page)

@admin.route("/flags/mark/user_flag/<flag_id>/")
@login_required
@authorize("resolve_user_flags")
def mark_user_flag(flag_id):
    flag = UserFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("admin.user_flags", user_id=flag.user_id))
    if flag.time_resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

@admin.route("/flags/mark_all/<user_id>/")
@login_required
@authorize("resolve_user_flags")
def mark_user_flags(user_id):
    user = User.query.get_or_404(user_id)
    redirect_url = generate_next(url_for("admin.user_flags", user_id=user.id))
    for flag in user.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

###############################
## Annotation Administration ##
###############################

@admin.route("/deactivate/annotation/<annotation_id>/")
@login_required
@authorize("deactivate_annotations")
def deactivate(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    annotation.active = not annotation.active
    db.session.commit()
    if annotation.active:
        flash(f"Annotation {annotation.id} activated")
    else:
        flash(f"Annotation {annotation.id} deactivated.")

    redirect_url = generate_next(url_for("annotation",
        annotation_id=annotation_id))
    return redirect(redirect_url)

@admin.route("/list/deactivated/annotations/")
@login_required
@authorize("view_deactivated_annotations")
def view_deactivated_annotations():
    sort = request.args.get("sort", "added", type=str)
    page = request.args.get("page", 1, type=int)
    if sort == "added":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.timestamp.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    elif sort == "weight":
        annotations = Annotation.query.filter_by(active=False
                ).order_by(Annotation.weight.desc()
                ).paginate(page, app.config["ANNOTATIONS_PER_PAGE"], False)
    sorts = {
            "added": url_for("admin.view_deactivated_annotations", page=page, sort="added"),
            "weight": url_for("admin.view_deactivated_annotations", page=page, sort="weight")
            }
    next_page = url_for("admin.view_deactivated_annotations", page=annotations.next_num,
            sort=sort) if annotations.has_next else None
    prev_page = url_for("admin.view_deactivated_annotations", page=annotations.prev_num,
            sort=sort) if annotations.has_prev else None
    uservotes = current_user.get_vote_dict() if current_user.is_authenticated \
            else None
    return render_template("indexes/annotation_list.html",
            title="Deactivated Annotations", annotations=annotations.items,
            prev_page=prev_page, next_page=next_page, uservotes=uservotes,
            sort=sort, sorts=sorts)

######################
## Annotation Flags ##
######################

@admin.route("/flags/annotation/all/")
@login_required
@authorize("resolve_annotation_flags")
def all_annotation_flags():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)

    if sort == "marked":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag":
        flags = AnnotationFlag.query\
                .outerjoin(AnnotationFlagEnum)\
                .order_by(AnnotationFlagEnum.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = AnnotationFlag.query\
                .outerjoin(AnnotationFlagEnum)\
                .order_by(AnnotationFlagEnum.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower":
        flags = AnnotationFlag.query\
                .outerjoin(User, User.id==AnnotationFlag.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = AnnotationFlag.query\
                .outerjoin(User, User.id==AnnotationFlag.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver":
        flags = AnnotationFlag.query\
                .outerjoin(User, User.id==AnnotationFlag.resolver_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = AnnotationFlag.query\
                .outerjoin(User, User.id==AnnotationFlag.resolver_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved_invert":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "annotation":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.annotation_id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "annotation_invert":
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.annotation_id.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "text":
        flags = AnnotationFlag.query\
                .join(Annotation,
                        Annotation.id==AnnotationFlag.annotation_id)\
                .join(Edition, Edition.id==Annotation.edition_id)\
                .join(Text, Text.id==Edition.text_id)\
                .order_by(Text.sort_title)\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        flags = AnnotationFlag.query\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("admin.all_annotation_flags", sort="marked", page=page),
            "marked_invert": url_for("admin.all_annotation_flags", sort="marked_invert", page=page),
            "flag": url_for("admin.all_annotation_flags", sort="flag", page=page),
            "flag_invert": url_for("admin.all_annotation_flags", sort="flag_invert", page=page),
            "time": url_for("admin.all_annotation_flags", sort="time", page=page),
            "time_invert": url_for("admin.all_annotation_flags", sort="time_invert", page=page),
            "thrower": url_for("admin.all_annotation_flags", sort="thrower", page=page),
            "thrower_invert": url_for("admin.all_annotation_flags", sort="thrower_invert", page=page),
            "resolver": url_for("admin.all_annotation_flags", sort="resolver", page=page),
            "resolver_invert": url_for("admin.all_annotation_flags", sort="resolver_invert", page=page),
            "time_resolved": url_for("admin.all_annotation_flags", sort="time_resolved", page=page),
            "time_resolved_invert": url_for("admin.all_annotation_flags", sort="time_resolved_invert", page=page),
            "annotation": url_for("admin.all_annotation_flags", sort="annotation", page=page),
            "annotation_invert": url_for("admin.all_annotation_flags", sort="annotation_invert", page=page),
            "text": url_for("admin.all_annotation_flags", sort="text", page=page),
            "text_invert": url_for("admin.all_annotation_flags", sort="text_invert", page=page),
            }

    next_page = url_for("admin.annotation_flags", annotation_id=annotation.id,
            page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for("admin.annotation_flags", annotation_id=annotation.id,
            page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template("indexes/all_annotation_flags.html",
            title=f"Annotation Flags", flags=flags.items, sort=sort,
            sorts=sorts, next_page=next_page, prev_page=prev_page)

@admin.route("/flags/annotation/<annotation_id>/")
@login_required
@authorize("resolve_annotation_flags")
def annotation_flags(annotation_id):
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "marked", type=str)
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("resolve_deactivated_annotation_flags")

    if sort == "marked":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "marked_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag":
        flags = annotation.flag_history\
                .outerjoin(AnnotationFlagEnum)\
                .order_by(AnnotationFlagEnum.flag.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "flag_invert":
        flags = annotation.flag_history\
                .outerjoin(AnnotationFlagEnum)\
                .order_by(AnnotationFlagEnum.flag.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_thrown.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_thrown.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlag.thrower_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "thrower_invert":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlag.thrower_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlag.resolver_id)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "resolver_invert":
        flags = annotation.flag_history\
                .outerjoin(User, User.id==AnnotationFlag.resolver_id)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_resolved_invert":
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_resolved.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        flags = annotation.flag_history\
                .order_by(AnnotationFlag.time_resolved.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)

    sorts = {
            "marked": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="marked", page=page),
            "marked_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="marked_invert", page=page),
            "flag": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="flag", page=page),
            "flag_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="flag_invert", page=page),
            "time": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="time", page=page),
            "time_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="time_invert", page=page),
            "thrower": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="thrower", page=page),
            "thrower_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="thrower_invert", page=page),
            "resolver": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="resolver", page=page),
            "resolver_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="resolver_invert", page=page),
            "time_resolved": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="time_resolved", page=page),
            "time_resolved_invert": url_for("admin.annotation_flags", annotation_id=annotation.id, sort="time_resolved_invert", page=page),
            }

    next_page = url_for("admin.annotation_flags", annotation_id=annotation.id,
            page=flags.next_num, sort=sort) if flags.has_next else None
    prev_page = url_for("admin.annotation_flags", annotation_id=annotation.id,
            page=flags.prev_num, sort=sort) if flags.has_prev else None
    return render_template("indexes/annotation_flags.html",
            title=f"Annotation {annotation.id} flags", annotation=annotation,
            flags=flags.items, sort=sort, sorts=sorts, next_page=next_page,
            prev_page=prev_page)

@admin.route("/flags/annotation/mark/<flag_id>/")
@login_required
@authorize("resolve_annotation_flags")
def mark_annotation_flag(flag_id):
    flag = AnnotationFlag.query.get_or_404(flag_id)
    redirect_url = generate_next(url_for("admin.annotation_flags",
        annotation_id=flag.annotation_id))
    if flag.time_resolved:
        flag.unresolve()
    else:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

@admin.route("/flags/annotation/<annotation_id>/mark/all/")
@login_required
@authorize("resolve_annotation_flags")
def mark_annotation_flags(annotation_id):
    annotation = Annotation.query.get_or_404(annotation_id)
    if not annotation.active:
        current_user.authorize("resolve_deactivated_annotation_flags")
    redirect_url = generate_next(url_for("admin.annotation_flags",
        annotation_id=annotation_id))
    for flag in annotation.active_flags:
        flag.resolve(current_user)
    db.session.commit()
    return redirect(redirect_url)

######################
## Wiki Edit Review ##
######################

@admin.route("/wiki/edits/review")
@login_required
@authorize("review_wiki_edits")
def wiki_edit_review_queue():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "voted", type=str)

    if sort == "voted":
        edits = WikiEdit.query.outerjoin(WikiEditVote,
                and_(WikiEditVote.voter_id==current_user.id,
                    WikiEditVote.edit_id==WikiEdit.id))\
                .filter(WikiEdit.approved==False, WikiEdit.rejected==False)\
                .order_by(WikiEditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "voted_invert":
        edits = WikiEdit.query.outerjoin(WikiEditVote,
                and_(WikiEditVote.voter_id==current_user.id,
                    WikiEditVote.edit_id==WikiEdit.id))\
                .filter(WikiEdit.approved==False, WikiEdit.rejected==False)\
                .order_by(WikiEditVote.delta.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "entity":
        edits = WikiEdit.query.outerjoin(Wiki).filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(Wiki.entity_string.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "entity_invert":
        edits = WikiEdit.query.outerjoin(Wiki).filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(Wiki.entity_string.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "num":
        edits = WikiEdit.query.filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(WikiEdit.num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "num_invert":
        edits = WikiEdit.query.filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(WikiEdit.num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = WikiEdit.query.outerjoin(User).filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = WikiEdit.query.outerjoin(User).filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = WikiEdit.query.filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(WikiEdit.timestamp.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = WikiEdit.query\
                .filter(WikiEdit.approved==False, WikiEdit.rejected==False)\
                .order_by(WikiEdit.timestamp.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = WikiEdit.query.filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(WikiEdit.reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = WikiEdit.query.filter(WikiEdit.approved==False,
                WikiEdit.rejected==False).order_by(WikiEdit.reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = WikiEdit.query.outerjoin(WikiEditVote,
                and_(WikiEditVote.voter_id==current_user.id,
                    WikiEditVote.edit_id==WikiEdit.id))\
                .filter(WikiEdit.approved==False, WikiEdit.rejected==False)\
                .order_by(WikiEditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
        sort = "voted"

    ids = [edit.id for edit in edits.items]

    votes = current_user.wiki_edit_votes\
            .filter(WikiEdit.id.in_(ids)).all()

    next_page = url_for("admin.wiki_edit_review_queue", page=edits.next_num,
            sort=sort) if edits.has_next else None
    prev_page = url_for("admin.wiki_edit_review_queue", page=edits.prev_num,
            sort=sort) if edits.has_prev else None

    return render_template("indexes/wiki_edit_review_queue.html",
            title="Wiki Edit Review Queue", edits=edits.items, votes=votes,
            sort=sort, next_page=next_page, prev_page=prev_page, page=page)

@admin.route("/wiki/<wiki_id>/edit/<edit_id>/review")
@login_required
@authorize("review_wiki_edits")
def review_wiki_edit(wiki_id, edit_id):
    edit = WikiEdit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for("view_wiki_edit", wiki_id=edit.wiki.id,
            edit_num=edit.num))

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.previous.body)
    diff2 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.body)

    diff = list(difflib.Differ().compare(diff1.splitlines(),
        diff2.splitlines()))

    return render_template("view/wiki_edit_review.html",
            title=f"Edit number {edit.num}", diff=diff, edit=edit)

@admin.route("/wiki/<wiki_id>/edit/<edit_id>/upvote")
@login_required
@authorize("review_wiki_edits")
def upvote_wiki_edit(wiki_id, edit_id):
    redirect_url = generate_next(url_for("index"))
    edit = WikiEdit.query.get(edit_id)
    if edit.approved:
        flash("That wiki edit has already been approved.")
    elif edit.rejected:
        flash("That wiki edit has already been rejected.")
    edit.upvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

@admin.route("/wiki/<wiki_id>/edit/<edit_id>/downvote")
@login_required
@authorize("review_wiki_edits")
def downvote_wiki_edit(wiki_id, edit_id):
    redirect_url = generate_next(url_for("index"))
    edit = WikiEdit.query.get(edit_id)
    if edit.approved:
        flash("That wiki edit has already been approved.")
    elif edit.rejected:
        flash("That wiki edit has already been rejected.")
    edit.downvote(current_user)
    db.session.commit()
    return redirect(redirect_url)

#################
## Edit Review ##
#################

@admin.route("/annotation/edits/review")
@login_required
@authorize("review_edits")
def edit_review_queue():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "voted", type=str)

    if sort == "voted":
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id))\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "voted_invert":
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id))\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "id":
        edits = Edit.query.outerjoin(Annotation)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Annotation.id.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "id_invert":
        edits = Edit.query.outerjoin(Annotation)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Annotation.id.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.num.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "edit_num_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.num.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor":
        edits = Edit.query.outerjoin(User)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(User.displayname.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "editor_invert":
        edits = Edit.query.outerjoin(User)\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(User.displayname.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.timestamp.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "time_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.timestamp.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.reason.asc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    elif sort == "reason_invert":
        edits = Edit.query\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(Edit.reason.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
    else:
        edits = Edit.query\
                .outerjoin(EditVote,
                        and_(EditVote.user_id==current_user.id,
                            EditVote.edit_id==Edit.id))\
                .filter(Edit.approved==False,
                        Edit.rejected==False)\
                .order_by(EditVote.delta.desc())\
                .paginate(page, app.config["NOTIFICATIONS_PER_PAGE"], False)
        sort = "voted"

    votes = current_user.edit_votes

    next_page = url_for("admin.edit_review_queue", page=edits.next_num, sort=sort)\
            if edits.has_next else None
    prev_page = url_for("admin.edit_review_queue", page=edits.prev_num, sort=sort)\
            if edits.has_prev else None

    return render_template("indexes/edit_review_queue.html",
            title="Edit Review Queue", edits=edits.items, votes=votes,
            sort=sort, next_page=next_page, prev_page=prev_page)

@admin.route("/annotation/<annotation_id>/edit/<edit_id>/review")
@login_required
@authorize("review_edits")
def review_edit(annotation_id, edit_id):

    edit = Edit.query.get_or_404(edit_id)
    if edit.approved == True:
        return redirect(url_for("view_edit", annotation_id=edit.annotation_id,
            num=edit.num))
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")

    # we have to replace single returns with spaces because markdown only
    # recognizes paragraph separation based on two returns. We also have to be
    # careful to do this for both unix and windows return variants (i.e. be
    # careful of \r's).
    diff1 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.previous.body)
    diff2 = re.sub(r"(?<!\n)\r?\n(?![\r\n])", " ", edit.body)

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

    return render_template("view/edit_review.html",
            title=f"[{edit.annotation.id}] Edit #{edit.num}",
            diff=diff, edit=edit, tags=tags, context=context)

@admin.route("/annotation/<annotation_id>/edit/<edit_id>/upvote")
@login_required
@authorize("review_edits")
def upvote_edit(annotation_id, edit_id):
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = generate_next(url_for("admin.review_edit", edit_id=edit.id))
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("admin.edit_review_queue"))
    edit.upvote(current_user)
    db.session.commit()
    return redirect(url_for("admin.edit_review_queue"))

@admin.route("/annotation/<annotation_id>/edit/<edit_id>/downvote")
@login_required
@authorize("review_edits")
def downvote_edit(annotation_id, edit_id):
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = generate_next(url_for("admin.review_edit", edit_id=edit.id))
    if not edit.annotation.active:
        current_user.authorize("review_deactivated_annotation_edits")
    elif edit.editor == current_user:
        flash("You cannot approve or reject your own edits")
        return redirect(url_for("admin.edit_review_queue"))
    edit.downvote(current_user)
    db.session.commit()
    return redirect(url_for("admin.edit_review_queue"))

#####################
## Content Editing ##
#####################

@admin.route("/edit/line/<line_id>/", methods=["GET", "POST"])
@login_required
@authorize("edit_lines")
def edit_line(line_id):
    line = Line.query.get_or_404(line_id)
    form = LineForm()
    form.line.data = line.line
    redirect_url = generate_next(url_for(line.get_url()))
    if form.validate_on_submit():
        if form.line.data != None and len(form.line.data) <= 200:
            line.line = form.line.data
            db.session.commit()
            flash("Line updated.")
            return redirect(redirect_url)
    return render_template("forms/line.html", title="Edit Line", form=form)

################
## Tag routes ##
################

@admin.route("/tags/create/", methods=["GET","POST"],
        defaults={"tag_request_id":None})
@admin.route("/tags/create/<tag_request_id>/", methods=["GET","POST"])
@login_required
@authorize("create_tags")
def create_tag(tag_request_id):
    tag_request = None
    if tag_request_id:
        tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for("tag_request_index"))
    form = TagForm()
    if form.validate_on_submit():
        if form.tag.data != None and form.description.data != None:
            tag = Tag(tag=form.tag.data, description=form.description.data)
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(redirect_url)
    elif tag_request:
            tag = Tag(tag=tag_request.tag, description=tag_request.description)
            tag_request.created_tag = tag
            tag_request.approved = True
            db.session.add(tag)
            db.session.commit()
            flash("Tag created.")
            return redirect(redirect_url)
    return render_template("forms/tag.html", title="Create Tag", form=form)

@admin.route("/tags/reject/<tag_request_id>/")
@login_required
@authorize("create_tags")
def reject_tag(tag_request_id):
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    redirect_url = generate_next(url_for("tag_request_index"))
    tag_request.rejected = True
    db.session.commit()
    return redirect(redirect_url)

##################################################################
## Delete routes (shouldn't be used unless absolutely necessary ##
##################################################################

@admin.route("/annotation/<annotation_id>/delete/", methods=["GET", "POST"])
@login_required
@authorize("delete_annotations")
def delete_annotation(annotation_id):
    form = AreYouSureForm()
    annotation = Annotation.query.get_or_404(annotation_id)
    redirect_url = url_for("text_annotations", text_url=annotation.text.url)
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
    return render_template("forms/delete_check.html", 
            title=f"Delete [{annotation_id}]", form=form, text=text)

@admin.route("/edit/<edit_id>/delete/", methods=["GET", "POST"])
@login_required
@authorize("delete_annotations")
def delete_edit(edit_id):
    form = AreYouSureForm()
    edit = Edit.query.get_or_404(edit_id)
    redirect_url = url_for("edit_history", annotation_id=edit.annotation_id)
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
    return render_template("forms/delete_check.html",
            title=f"Delete edit #{edit.num} of [{edit.annotation_id}]",
            form=form, text=text)

@admin.route("/wiki/edit/<edit_id>/delete", methods=["GET", "POST"])
@login_required
@authorize("delete_wiki_edits")
def delete_wiki_edit(edit_id):
    form = AreYouSureForm()
    edit = WikiEdit.query.get_or_404(edit_id)
    redirect_url = url_for("wiki_edit_history", wiki_id=edit.wiki.id)
    if form.validate_on_submit():
        if edit.current:
            edit.previous.current = True
        else:
            for e in edit.wiki.edits.order_by(WikiEdit.num.desc()).all():
                if e.num > edit.num:
                    e.num -= 1
        flash(f"Edit #{edit.num} of {str(edit.wiki.entity)} deleted.")
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
    return render_template("forms/delete_check.html",
            title=f"Delete wiki edit #{edit.num}", form=form, text=text)

@admin.route("/request/text/<text_request_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_text_request(text_request_id):
    form = AreYouSureForm()
    text_request = TextRequest.query.get_or_404(text_request_id)
    if not current_user == text_request.requester:
        current_user.authorize("delete_text_requests")
    redirect_url = url_for("text_request_index")
    if form.validate_on_submit():
        flash(f"Book Request for {text_request.title} deleted.")
        db.session.delete(text_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the text request and all of it's votes will be deleted
permanently.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete Book Request", form=form, text=text)

@admin.route("/request/tag/<tag_request_id>/delete/", methods=["GET", "POST"])
@login_required
def delete_tag_request(tag_request_id):
    form = AreYouSureForm()
    tag_request = TagRequest.query.get_or_404(tag_request_id)
    if not current_user == tag_request.requester:
        current_user.authorize("delete_tag_requests")
    redirect_url = url_for("tag_request_index")
    if form.validate_on_submit():
        flash(f"Tag Request for {tag_request.tag} deleted.")
        db.session.delete(tag_request)
        db.session.commit()
        return redirect(redirect_url)
    text = """
If you click submit the text request and all of it's votes will be deleted
permanently.
    """
    return render_template("forms/delete_check.html", 
            title=f"Delete Tag Request", form=form, text=text)
