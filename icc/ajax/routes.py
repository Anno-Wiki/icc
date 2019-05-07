"""The ajax routes."""
import time

from flask import request, jsonify, current_app, get_flashed_messages, flash
from icc.models.annotation import Tag
from icc.ajax import ajax


@ajax.route('/autocomplete/tags/', methods=['POST'])
def tags():
    """This route provides json to populate an autocomplete tag entry similar to
    stackoverflow (which still needs work).
    """
    tagstr = request.form.get('tags')
    tags = tagstr.split()
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
