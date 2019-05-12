"""The ajax routes."""
import time
from datetime import datetime

from flask import request, jsonify, current_app, get_flashed_messages, flash
from flask_login import current_user, login_required

from icc import db, classes
from icc.models.annotation import Tag
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


@ajax.route('/vote')
def vote():
    """All ajax voting routes in one!"""
    entity_cls = classes.get(request.args.get('entity'), None)
    entity_id = request.args.get('id').strip('[a-z]')
    if not entity_cls:
        return jsonify({'success': False, 'rollback': False,
                        'status': 'not-a-thing'})
    if not isinstance(entity_cls, classes['VotableMixin']):
        return jsonify({'success': False, 'rollback': False,
                        'status': 'not-votable'})
    if not current_user.is_authenticated:
        flash(f"You must login to vote.")
        return jsonify({'success': False, 'rollback': False, 'status': 'login'})
    entity = entity_cls.query.get_or_404(entity_id)
    original_weight = entity.weight
    vote = current_user.get_vote(entity)
    if isinstance(entity, classes['Annotation']) and not entity.active:
        flash("You cannot vote on deactivated annotations.")
        return jsonify({'success': False, 'rollback': False,
                        'status': 'deactivated'})
    up = bool(request.args.get('up'))
    status = (entity.upvote(current_user) if up else
              annotation.downvote(current_user))
    db.session.commit()
    new_weight = entity.weight
    return jsonify(status)


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
