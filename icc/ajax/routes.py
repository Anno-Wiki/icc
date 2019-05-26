"""The ajax routes."""
import time
from string import ascii_lowercase as lowercase
from datetime import datetime

from flask import request, jsonify, current_app, get_flashed_messages, flash
from flask_login import current_user, login_required

from icc import db, classes
from icc.models.annotation import Tag
from icc.models.content import Edition, TOC
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
    return jsonify(messages)


@ajax.route('/vote')
def vote():
    """All ajax voting routes in one!"""
    entity_cls = classes.get(request.args.get('entity'), None)
    entity_id = request.args.get('id').strip(lowercase)
    if not entity_cls:
        return jsonify({'success': False, 'rollback': False,
                        'status': 'not-a-thing'})
    if not issubclass(entity_cls, classes['VotableMixin']):
        return jsonify({'success': False, 'rollback': False,
                        'status': 'not-votable'})
    if not current_user.is_authenticated:
        flash(f"You must login to vote.")
        return jsonify({'success': False, 'rollback': False, 'status': 'login'})
    entity = entity_cls.query.get(entity_id)
    original_weight = entity.weight
    vote = current_user.get_vote(entity)
    if isinstance(entity, classes['Annotation']) and not entity.active:
        flash("You cannot vote on deactivated annotations.")
        return jsonify({'success': False, 'rollback': False,
                        'status': 'deactivated'})
    up = True if request.args.get('up').lower() == 'true' else False
    status = (entity.upvote(current_user) if up else
              entity.downvote(current_user))
    db.session.commit()
    new_weight = entity.weight
    change = new_weight - original_weight
    status['change'] = change
    return jsonify(status)


@ajax.route('/follow')
def follow():
    entity_cls = classes.get(request.args.get('entity'), None)
    entity_id = request.args.get('id').strip(lowercase)
    if not entity_cls:
        return jsonifY({'success': False, 'status': 'no-class'})
    if not issubclass(entity_cls, classes['FollowableMixin']):
        return jsonifY({'success': False, 'status': 'not-followable'})
    entity = entity_cls.query.get_or_404(entity_id)
    followings = getattr(current_user,
                         f'followed_{entity_cls.__name__.lower()}s')
    if entity in followings:
        followings.remove(entity)
        status = 'follow'
    else:
        followings.append(entity)
        status = 'unfollow'
    db.session.commit()
    return jsonify({'success': True, 'status': status})


@ajax.route('/edition/<edition_id>/<toc_id>/line')
def line(edition_id, toc_id):
    edition = Edition.query.get(edition_id)
    if not edition:
        return jsonify({'success': False})
    num = request.args.get('num')
    line = edition.lines.filter_by(num=num).first()
    if not line:
        return jsonify({'success': False})
    if not line.toc_id == int(toc_id):
        print(line.toc_id)
        return jsonify({'success': False})
    return jsonify({'success': True, 'line': line.body,
                    'enum': str(line.enum) })


server_start_time = time.time()


@ajax.route('/heartbeat', methods=['GET'])
def heartbeat():
    """This route provides a json object that includes the last server restart
    time. This is to refresh the app.
    """
    if current_app.config["DEBUG"]:
        return jsonify({'start_time': server_start_time})
    return jsonify({'start_time': "No way, José."})
