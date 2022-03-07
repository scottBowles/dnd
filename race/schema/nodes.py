from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from ..models import Race, Trait


class TraitNode(DjangoObjectType):
    class Meta:
        model = Trait
        fields = ("id", "name", "description")
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class RaceNode(DjangoObjectType):
    class Meta:
        model = Race
        fields = (
            "id",
            "name",
            "age_of_adulthood",
            "life_expectancy",
            "alignment",
            "size",
            "speed",
            "languages",
            "traits",
            "base_race",
            "subraces",
        )
        filter_fields = []
        interfaces = (relay.Node,)
