import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import RaceNode


class RaceQuery(graphene.ObjectType):
    race = relay.Node.Field(RaceNode)
    races = DjangoFilterConnectionField(RaceNode)


class Query(
    RaceQuery,
    graphene.ObjectType,
):
    pass
