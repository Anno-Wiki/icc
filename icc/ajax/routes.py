"""The ajax routes."""
import time
from datetime import datetime

from flask import request, jsonify, current_app, get_flashed_messages, flash
from flask_login import current_user, login_required

from icc import db
from icc.models.annotation import Tag, Annotation
from icc.models.content import Edition
from icc.ajax import ajax


@ajax.route('/autocomplete/tags/', methods=['POST'])
def tags():
    """This route provides json to populate an autocomplete tag entry similar to
    stackoverflow (which still needs work).
    """
    tagstr = request.form.get('tags')
    tags = tagstr.split()
    if not tags:
        tags = [""]
    results = Tag.query.filter(Tag.tag.startswith(tags[-1]),
                               Tag.locked==False).limit(6)
    if not results:
        return jsonify({'success': False, 'tags': []})
    tag_list = []
    descriptions = []
    for t in results:
        tag_list.append(t.tag)
        if len(t.wiki.current.body) > 500:
            descriptions.append(t.wiki.current.body[:500])
        else:
            descriptions.append(t.wiki.current.body)

    return jsonify({'success': True, 'tags': tag_list,
                    'descriptions': descriptions})


@ajax.route('/flashed', methods=['GET'])
def flashed():
    """This route is an ajax way to get the flashed messages."""
    messages = get_flashed_messages(with_categories=True)
    print(messages)
    return jsonify(messages)


def vote(upvote):
    """The actual voting method. Quite simple, really."""
    annotation_id = request.args.get('id').strip('a')
    if not current_user.is_authenticated:
        flash(f"You must login to vote.")
        return jsonify({'situ': ['failure', 'login']})
    annotation = Annotation.query.get_or_404(annotation_id)
    original_weight = annotation.weight
    vote = current_user.get_vote(annotation)
    if not annotation.active:
        flash("You cannot vote on deactivated annotations.")
        return jsonify({'situ': ['deactivated', 'failure']})
    elif vote:
        diff = datetime.utcnow() - vote.timestamp
        if diff.days > 0 and annotation.HEAD.timestamp < vote.timestamp:
            flash("Your vote is locked until the annotation is modified.")
            return jsonify({'situ': ['locked-in', 'failure']})
    if upvote:
        situ = annotation.upvote(current_user)
    else:
        situ = annotation.downvote(current_user)
    db.session.commit()
    new_weight = annotation.weight
    return jsonify({'situ': situ, 'change': new_weight - original_weight})


@ajax.route('/annotation/upvote')
def upvote_annotation():
    """Upvote ajax style. I really like how simple this is, lol."""
    return vote(upvote=True)


@ajax.route('/annotation/downvote')
def downvote_annotation():
    """Downvote ajax style."""
    return vote(upvote=False)


@ajax.route('edition/<edition_id>/line')
def line(edition_id):
    edition = Edition.query.get(edition_id)
    if not edition:
        return jsonify({'success': False})
    num = request.args.get('num')
    line = edition.lines.filter_by(num=num).first()
    if not line:
        return jsonify({'success': False})
    return jsonify({'success': True, 'line': line.line,
                    'enum': line.primary.enum })





server_start_time = time.time()

@ajax.route('/heartbeat', methods=['GET'])
def heartbeat():
    """This route provides a json object that includes the last server restart
    time. This is to refresh the app.
    """
    if current_app.config["DEBUG"]:
        return jsonify({'start_time': server_start_time})
    else:
        return jsonify({'start_time': "No way, José."})
