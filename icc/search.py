"""A module devoted to my search system."""
import string

from flask import current_app
from elasticsearch import helpers
from icc import models, db


def bulk_index(index, objs):
    """Add objects to the index in bulk."""
    if not current_app.elasticsearch:
        return
    if not current_app.elasticsearch.indices.exists(index):
        current_app.elasticsearch.indices.create(index)
    actions = []
    for obj in objs:
        payload = {}
        for field in obj.__searchable__:
            try:
                data = getattr(obj, field)
            except AttributeError:
                print(obj)
                print(obj.id)
                raise AttributeError
            payload[field] = (data.translate(
                str.maketrans('', '', string.punctuation))
                              if isinstance(data, str) else data)
        actions.append(
            {'_index': index, '_type': index,
             '_id': obj.id, '_source': payload})
    helpers.bulk(current_app.elasticsearch, actions)


def add_to_index(index, model):
    """Add an object to the index for that object."""
    if not current_app.elasticsearch:
        return
    if not current_app.elasticsearch.indices.exists(index):
        current_app.elasticsearch.indices.create(index)
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, doc_type=index, id=model.id,
                                    body=payload)


def remove_from_index(index, model):
    """Remove the object from the index."""
    if not current_app.elasticsearch:
        return
    if not current_app.elasticsearch.indices.exists(index):
        current_app.elasticsearch.indices.create(index)
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)


def query_index(index, query, page, per_page):
    """Search the index."""
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index, doc_type=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']


def query_lines(field, query, page, per_page):
    """Search lines within a given object (text, writer, edition)"""
    if not current_app.elasticsearch:
        return [], 0
    Line = models.content.Line # Hack to avoid circular import
    body = {'query':
            {'bool':
             {'must':
              [
                  {'match': {f'{field.__tablename__}_id': field.id}},
                  {'match': {'body': query}}
              ]
              }
             },
            'from': (page - 1) * per_page, 'size': per_page
            }
    search = current_app.elasticsearch.search(index='line', doc_type='line',
                                              body=body)

    total = search['hits']['total']
    if isinstance(total, dict):
        total = total.get('value', 0)
    if total == 0:
        return Line.query.filter_by(id=0), 0

    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    when = []
    when = [(ids[i], i) for i in range(len(ids))]

    return Line.query.filter(Line.id.in_(ids))\
        .order_by(db.case(when, value=Line.id)).all(), total
