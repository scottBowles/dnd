import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..models import (
    Item,
    ArtifactTraits,
    ArmorTraits,
    WeaponTraits,
    EquipmentTraits,
    Artifact,
    Armor,
    Weapon,
    Equipment,
)


class ArtifactTraitsNode(DjangoObjectType):
    class Meta:
        model = ArtifactTraits
        fields = ("notes",)
        interfaces = (relay.Node,)


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
    artifact = graphene.Field(ArtifactTraitsNode)
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
            "artifact",
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


class ArtifactNode(ItemNodeBase, DjangoObjectType):
    class Meta(ItemNodeBase.Meta):
        model = Artifact


class ArmorNode(ItemNodeBase, DjangoObjectType):
    class Meta(ItemNodeBase.Meta):
        model = Armor


class EquipmentNode(ItemNodeBase, DjangoObjectType):
    class Meta(ItemNodeBase.Meta):
        model = Equipment


class WeaponNode(ItemNodeBase, DjangoObjectType):
    class Meta(ItemNodeBase.Meta):
        model = Weapon
