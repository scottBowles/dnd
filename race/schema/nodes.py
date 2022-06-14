import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from ..models import Race, Trait, AbilityScoreIncrease
from nucleus.utils import login_or_queryset_none


class AbilityScoreIncreaseNode(DjangoObjectType):
    class Meta:
        model = AbilityScoreIncrease
        fields = ("id", "ability_score", "increase")
        filter_fields = ["ability_score"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class TraitNode(DjangoObjectType):
    class Meta:
        model = Trait
        fields = ("id", "name", "description")
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class RaceNode(DjangoObjectType):
    locked_by_self = graphene.Boolean()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = Race
        fields = (
            "id",
            "name",
            "description",
            "image_ids",
            "thumbnail_id",
            "age_of_adulthood",
            "life_expectancy",
            "ability_score_increases",
            "alignment",
            "size",
            "speed",
            "languages",
            "traits",
            "base_race",
            "subraces",
            "markdown_notes",
            "lock_user",
            "lock_time",
            "logs",
        )
        filter_fields = []
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset
