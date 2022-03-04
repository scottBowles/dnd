import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from .nodes import NPCNode, FeatureNode, SkillNode, LanguageNode, ProficiencyNode

# from .nodes import (
#     ItemNode,
#     # ArtifactNode,
#     # ArmorNode,
#     # WeaponNode,
#     # EquipmentNode,
# )


class NPCQuery(graphene.ObjectType):
    npc = relay.Node.Field(NPCNode)
    npc_list = DjangoFilterConnectionField(NPCNode)


class FeatureQuery(graphene.ObjectType):
    feature = relay.Node.Field(FeatureNode)
    features = DjangoFilterConnectionField(FeatureNode)


class SkillQuery(graphene.ObjectType):
    skill = relay.Node.Field(SkillNode)
    skills = DjangoFilterConnectionField(SkillNode)


class LanguageQuery(graphene.ObjectType):
    language = relay.Node.Field(LanguageNode)
    languages = DjangoFilterConnectionField(LanguageNode)


class ProficiencyQuery(graphene.ObjectType):
    proficiency = relay.Node.Field(ProficiencyNode)
    proficiencies = DjangoFilterConnectionField(ProficiencyNode)


# class ItemQuery(graphene.ObjectType):
#     item = relay.Node.Field(ItemNode)
#     items = DjangoFilterConnectionField(ItemNode)


# # class ArtifactQuery(graphene.ObjectType):
# #     artifact = relay.Node.Field(ArtifactNode)
# #     artifacts = DjangoFilterConnectionField(ArtifactNode)


# # class ArmorQuery(graphene.ObjectType):
# #     armor = relay.Node.Field(ArmorNode)
# #     armors = DjangoFilterConnectionField(ArmorNode)


# # class WeaponQuery(graphene.ObjectType):
# #     weapon = relay.Node.Field(WeaponNode)
# #     weapons = DjangoFilterConnectionField(WeaponNode)


# # class EquipmentQuery(graphene.ObjectType):
# #     equipment = relay.Node.Field(EquipmentNode)
# #     equipments = DjangoFilterConnectionField(EquipmentNode)


# class Query(
#     ItemQuery,
#     # ArtifactQuery,
#     # ArmorQuery,
#     # WeaponQuery,
#     # EquipmentQuery,
#     graphene.ObjectType,
# ):
#     pass


class Query(
    NPCQuery,
    FeatureQuery,
    SkillQuery,
    ProficiencyQuery,
    LanguageQuery,
    graphene.ObjectType,
):
    pass
