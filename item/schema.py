import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Item, ArtifactTraits, ArmorTraits, WeaponTraits, EquipmentTraits


class ItemNode(DjangoObjectType):
    class Meta:
        model = Item
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


class Query(graphene.ObjectType):
    item = relay.Node.Field(ItemNode)
    items = DjangoFilterConnectionField(ItemNode)


schema = graphene.Schema(query=Query)
