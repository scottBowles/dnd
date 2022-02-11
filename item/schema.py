import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Item, ArtifactTraits, ArmorTraits, WeaponTraits, EquipmentTraits
from .serializers import ItemSerializerGQL
from nucleus.utils import RelayCUD


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


class ArtifactInput(graphene.InputObjectType):
    notes = graphene.String()


class ArmorInput(graphene.InputObjectType):
    ac_bonus = graphene.Int()


class EquipmentInput(graphene.InputObjectType):
    brief_description = graphene.String()


class WeaponInput(graphene.InputObjectType):
    attack_bonus = graphene.Int()


class Input:
    name = graphene.String()
    description = graphene.String()
    artifact = ArtifactInput(required=False)
    armor = ArmorInput(required=False)
    equipment = EquipmentInput(required=False)
    weapon = WeaponInput(required=False)


mutations = RelayCUD("item", ItemNode, Input, Item, ItemSerializerGQL)


class Mutation(graphene.ObjectType):
    item_create = mutations.create_mutation().Field()
    item_update = mutations.update_mutation().Field()
    item_patch = mutations.partial_update_mutation().Field()
    item_delete = mutations.delete_mutation().Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
