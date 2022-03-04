import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..models import NPC, Feature, Skill, Script, Language, Proficiency

# from ..models import (
#     Item,
#     ArtifactTraits,
#     ArmorTraits,
#     WeaponTraits,
#     EquipmentTraits,
#     Artifact,
#     Armor,
#     Weapon,
#     Equipment,
# )


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
        filter_fields = ["name"]
        interfaces = (relay.Node,)


class LanguageNode(DjangoObjectType):
    script = graphene.Field(ScriptNode)

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


# class ArtifactTraitsNode(DjangoObjectType):
#     class Meta:
#         model = ArtifactTraits
#         fields = ("notes",)
#         interfaces = (relay.Node,)


# class ArmorTraitsNode(DjangoObjectType):
#     class Meta:
#         model = ArmorTraits
#         fields = ("ac_bonus",)
#         interfaces = (relay.Node,)


# class WeaponTraitsNode(DjangoObjectType):
#     class Meta:
#         model = WeaponTraits
#         fields = ("attack_bonus",)
#         interfaces = (relay.Node,)


# class EquipmentTraitsNode(DjangoObjectType):
#     class Meta:
#         model = EquipmentTraits
#         fields = ("brief_description",)
#         interfaces = (relay.Node,)


# class ItemNodeBase:
#     artifact = graphene.Field(ArtifactTraitsNode)
#     armor = graphene.Field(ArmorTraitsNode)
#     weapon = graphene.Field(WeaponTraitsNode)
#     equipment = graphene.Field(EquipmentTraitsNode)

#     class Meta:
#         fields = (
#             "id",
#             "name",
#             "description",
#             "created",
#             "updated",
#             "artifact",
#             "armor",
#             "weapon",
#             "equipment",
#         )
#         filter_fields = [
#             "name",
#             "description",
#             "created",
#             "updated",
#         ]
#         interfaces = (relay.Node,)


# class ItemNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Item


# class ArtifactNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Artifact


# class ArmorNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Armor


# class EquipmentNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Equipment


# class WeaponNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Weapon
