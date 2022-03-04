import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import (
    ItemNode,
    # ArtifactNode,
    # ArmorNode,
    # WeaponNode,
    # EquipmentNode,
)


class ItemQuery(graphene.ObjectType):
    item = relay.Node.Field(ItemNode)
    items = DjangoFilterConnectionField(ItemNode)


# class ArtifactQuery(graphene.ObjectType):
#     artifact = relay.Node.Field(ArtifactNode)
#     artifacts = DjangoFilterConnectionField(ArtifactNode)


# class ArmorQuery(graphene.ObjectType):
#     armor = relay.Node.Field(ArmorNode)
#     armors = DjangoFilterConnectionField(ArmorNode)


# class WeaponQuery(graphene.ObjectType):
#     weapon = relay.Node.Field(WeaponNode)
#     weapons = DjangoFilterConnectionField(WeaponNode)


# class EquipmentQuery(graphene.ObjectType):
#     equipment = relay.Node.Field(EquipmentNode)
#     equipments = DjangoFilterConnectionField(EquipmentNode)


class Query(
    ItemQuery,
    # ArtifactQuery,
    # ArmorQuery,
    # WeaponQuery,
    # EquipmentQuery,
    graphene.ObjectType,
):
    pass
