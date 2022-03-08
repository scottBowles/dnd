import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import RaceNode, TraitNode, AbilityScoreIncreaseNode


class AbilityScoreIncreaseQuery(graphene.ObjectType):
    ability_score_increase = relay.Node.Field(AbilityScoreIncreaseNode)
    ability_score_increases = DjangoFilterConnectionField(AbilityScoreIncreaseNode)


class TraitQuery(graphene.ObjectType):
    trait = relay.Node.Field(TraitNode)
    traits = DjangoFilterConnectionField(TraitNode)


class RaceQuery(graphene.ObjectType):
    race = relay.Node.Field(RaceNode)
    races = DjangoFilterConnectionField(RaceNode)


class Query(
    AbilityScoreIncreaseQuery,
    TraitQuery,
    RaceQuery,
    graphene.ObjectType,
):
    pass
