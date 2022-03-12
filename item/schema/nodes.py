import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..models import Item, ArmorTraits, WeaponTraits, EquipmentTraits, Artifact


class ArmorTraitsNode(DjangoObjectType):
    class Meta:
        model = ArmorTraits
        fields = ("ac_bonus",)
        interfaces = (relay.Node,)


class WeaponTraitsNode(DjangoObjectType):
    class Meta:
        model = WeaponTraits
        fields = ("attack_bonus",)
        interfaces = (relay.Node,)


class EquipmentTraitsNode(DjangoObjectType):
    class Meta:
        model = EquipmentTraits
        fields = ("brief_description",)
        interfaces = (relay.Node,)


class ItemNodeBase:
    armor = graphene.Field(ArmorTraitsNode)
    weapon = graphene.Field(WeaponTraitsNode)
    equipment = graphene.Field(EquipmentTraitsNode)

    class Meta:
        fields = (
            "id",
            "name",
            "description",
            "created",
            "updated",
            "armor",
            "weapon",
            "equipment",
        )
        filter_fields = [
            "name",
            "description",
            "created",
            "updated",
        ]
        interfaces = (relay.Node,)


class ItemNode(ItemNodeBase, DjangoObjectType):
    class Meta(ItemNodeBase.Meta):
        model = Item


class ArtifactNode(DjangoObjectType):
    class Meta:
        model = Artifact
        fields = (
            "items",
            "notes",
            "name",
            "description",
            "created",
            "updated",
        )
        filter_fields = [
            "name",
            "created",
        ]
        interfaces = (relay.Node,)
