import graphene

from nucleus.utils import RelayCUD
from ..models import Item
from ..serializers import ItemSerializerGQL
from .nodes import ItemNode


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


ItemMutations = RelayCUD(
    "item", ItemNode, Input, Item, ItemSerializerGQL
).get_mutation_class()


class Mutation(
    ItemMutations,
    graphene.ObjectType,
):
    pass
