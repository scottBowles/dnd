from graphene import relay
from graphene_django import DjangoObjectType

from ..models import NPC, Feature, Skill, Script, Language, Proficiency


class FeatureNode(DjangoObjectType):
    class Meta:
        model = Feature
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class SkillNode(DjangoObjectType):
    class Meta:
        model = Skill
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class ProficiencyNode(DjangoObjectType):
    class Meta:
        model = Proficiency
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class ScriptNode(DjangoObjectType):
    class Meta:
        model = Script
        fields = ("id", "name")
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class LanguageNode(DjangoObjectType):
    class Meta:
        model = Language
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class FeaturesAndTraitConnection(relay.Connection):
    class Meta:
        node = FeatureNode


class ProficiencyConnection(relay.Connection):
    class Meta:
        node = ProficiencyNode


class NPCNode(DjangoObjectType):
    features_and_traits = relay.ConnectionField(FeaturesAndTraitConnection)
    profiencies = relay.ConnectionField(ProficiencyConnection)

    def resolve_features_and_traits(self, info, **kwargs):
        return self.features_and_traits.all()

    def resolve_profiencies(self, info, **kwargs):
        return self.profiencies.all()

    class Meta:
        model = NPC
        filter_fields = ["name"]
        interfaces = (relay.Node,)
