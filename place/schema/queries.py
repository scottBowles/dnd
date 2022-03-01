import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import ExportNode, PlaceNode


class PlaceQuery(graphene.ObjectType):
    place = relay.Node.Field(PlaceNode)
    places = DjangoFilterConnectionField(PlaceNode)


class ExportQuery(graphene.ObjectType):
    export = relay.Node.Field(ExportNode)
    exports = DjangoFilterConnectionField(ExportNode)


class Query(
    ExportQuery,
    PlaceQuery,
    graphene.ObjectType,
):
    pass
