from flask import request, jsonify
from app import app, db
from app.models import Tag
from . import ajax

@ajax.route("/autocomplete/tags/", methods=["POST"])
def ajax_tags():
    tagstr = request.form.get("tags")
    tags = tagstr.split()
    results = Tag.query.filter(Tag.tag.startswith(tags[-1]), Tag.admin==False)\
            .limit(6)
    if not results:
        return jsonify({"success": False, "tags": []})
    tag_list = []
    descriptions = []
    for t in results:
        tag_list.append(t.tag)
        descriptions.append(t.description)

    return jsonify({"success": True, "tags": tag_list,
        "descriptions": descriptions })
