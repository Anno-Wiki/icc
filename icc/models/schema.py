import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField

from .content import Line as LineModel

class Line(SQLAlchemyObjectType):
    class Meta:
        model = LineModel
        interfaces = (relay.Node,)

class Query(graphene.ObjectType):
    node = relay.Node.Field()
    all_lines = SQLAlchemyConnectionField(Line.connection)

schema = graphene.Schema(query=Query)
