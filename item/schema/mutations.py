import graphene

from nucleus.utils import RelayCUD, ConcurrencyLockActions
from ..models import Item
from ..serializers import ItemSerializer
from .nodes import ItemNode


class ArtifactInput(graphene.InputObjectType):
    notes = graphene.String()
    markdown_notes = graphene.String()


class ArmorInput(graphene.InputObjectType):
    ac_bonus = graphene.Int()


class EquipmentInput(graphene.InputObjectType):
    brief_description = graphene.String()


class WeaponInput(graphene.InputObjectType):
    attack_bonus = graphene.Int()


class ItemCUD(RelayCUD):
    field = "item"
    Node = ItemNode
    model = Item
    serializer_class = ItemSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_id = graphene.String()
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()
        artifact = ArtifactInput(required=False)
        armor = ArmorInput(required=False)
        equipment = EquipmentInput(required=False)
        weapon = WeaponInput(required=False)


class ItemConcurrencyLock(ConcurrencyLockActions):
    field = "item"
    model = Item


ItemCUDMutations = ItemCUD().get_mutation_class()
ItemLockMutations = ItemConcurrencyLock().get_mutation_class()


class Mutation(ItemCUDMutations, ItemLockMutations, graphene.ObjectType):
    pass
