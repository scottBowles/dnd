import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..models import NPC, Feature, Skill, Script, Language, Proficiency
from nucleus.utils import login_or_queryset_none


class FeatureNode(DjangoObjectType):
    class Meta:
        model = Feature
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class SkillNode(DjangoObjectType):
    class Meta:
        model = Skill
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class ProficiencyNode(DjangoObjectType):
    class Meta:
        model = Proficiency
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class ScriptNode(DjangoObjectType):
    class Meta:
        model = Script
        fields = ("id", "name")
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class LanguageNode(DjangoObjectType):
    class Meta:
        model = Language
        fields = ("id", "name", "description", "script")
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class FeaturesAndTraitConnection(relay.Connection):
    class Meta:
        node = FeatureNode


class ProficiencyConnection(relay.Connection):
    class Meta:
        node = ProficiencyNode


class NPCNode(DjangoObjectType):
    features_and_traits = relay.ConnectionField(FeaturesAndTraitConnection)
    profiencies = relay.ConnectionField(ProficiencyConnection)
    locked_by_self = graphene.Boolean()

    def resolve_features_and_traits(self, info, **kwargs):
        return self.features_and_traits.all()

    def resolve_profiencies(self, info, **kwargs):
        return self.profiencies.all()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = NPC
        filter_fields = ["name"]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset
