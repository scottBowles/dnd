import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import PlaceNode


class PlaceQuery(graphene.ObjectType):
    place = relay.Node.Field(PlaceNode)
    places = DjangoFilterConnectionField(PlaceNode)


class Query(
    PlaceQuery,
    graphene.ObjectType,
):
    pass
