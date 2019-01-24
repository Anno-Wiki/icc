from flask import request, jsonify
from icc.models import Tag
from icc.ajax import ajax


@ajax.route('/autocomplete/tags/', methods=['POST'])
def ajax_tags():
    tagstr = request.form.get('tags')
    tags = tagstr.split()
    results = Tag.query.filter(Tag.tag.startswith(tags[-1]),
                               Tag.locked==False).limit(6)
    print(results)
    if not results:
        return jsonify({'success': False, 'tags': []})
    tag_list = []
    descriptions = []
    for t in results:
        tag_list.append(t.tag)
        descriptions.append(t.wiki.current.body)

    return jsonify({'success': True, 'tags': tag_list,
                    'descriptions': descriptions})
