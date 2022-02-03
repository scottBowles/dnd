import graphene
from graphene_django import DjangoObjectType

from .models import Item, ArtifactTraits, ArmorTraits, WeaponTraits, EquipmentTraits


class ItemType(DjangoObjectType):
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


class ArtifactTraitsType(DjangoObjectType):
    class Meta:
        model = ArtifactTraits
        fields = ("notes",)


class ArmorType(DjangoObjectType):
    class Meta:
        model = ArmorTraits
        fields = ("ac_bonus",)


class WeaponTraitsType(DjangoObjectType):
    class Meta:
        model = WeaponTraits
        fields = ("attack_bonus",)


class EquipmentTraitsType(DjangoObjectType):
    class Meta:
        model = EquipmentTraits
        fields = ("brief_description",)


class Query(graphene.ObjectType):
    items = graphene.List(ItemType)
    item_by_id = graphene.Field(ItemType, id=graphene.Int())

    def resolve_items(self, info):
        return Item.objects.all()

    def resolve_item_by_id(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return Item.objects.get(pk=id)
        return None


schema = graphene.Schema(query=Query)
