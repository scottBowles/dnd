import graphene

from nucleus.utils import RelayCUD, ConcurrencyLockActions, ImageMutations
from ..models import Artifact, Item
from ..serializers import ArtifactSerializer, ItemSerializer
from .nodes import ArtifactNode, ItemNode


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
        image_ids = graphene.List(graphene.String)
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()
        artifact = ArtifactInput(required=False)
        armor = ArmorInput(required=False)
        equipment = EquipmentInput(required=False)
        weapon = WeaponInput(required=False)


class ItemConcurrencyLock(ConcurrencyLockActions):
    field = "item"
    Node = ItemNode
    model = Item


class ItemImageMutations(ImageMutations):
    field = "item"
    Node = ItemNode
    model = Item


ItemImageMutations = ItemImageMutations().get_mutation_class()

ItemCUDMutations = ItemCUD().get_mutation_class()
ItemLockMutations = ItemConcurrencyLock().get_mutation_class()


class ArtifactCUD(RelayCUD):
    field = "artifact"
    Node = ArtifactNode
    model = Artifact
    serializer_class = ArtifactSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_ids = graphene.List(graphene.String)
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()
        notes = graphene.String()
        items = graphene.List(graphene.String)


class ArtifactConcurrencyLock(ConcurrencyLockActions):
    field = "artifact"
    Node = ArtifactNode
    model = Artifact


class ArtifactImageMutations(ImageMutations):
    field = "artifact"
    Node = ArtifactNode
    model = Artifact


ArtifactCUDMutatons = ArtifactCUD().get_mutation_class()
ArtifactLockMutations = ArtifactConcurrencyLock().get_mutation_class()
ArtifactImageMutations = ArtifactImageMutations().get_mutation_class()


class Mutation(
    ArtifactCUDMutatons,
    ArtifactLockMutations,
    ArtifactImageMutations,
    ItemCUDMutations,
    ItemLockMutations,
    ItemImageMutations,
    graphene.ObjectType,
):
    pass
