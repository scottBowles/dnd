from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from ..models import Place, PlaceExport, Export, PlaceRace, PlaceAssociation
from race.models import Race
from association.schema import AssociationNode


class RaceNode(DjangoObjectType):
    """
    Eventually this should come from the Race app's RaceNode
    """

    class Meta:
        model = Race
        fields = (
            "id",
            "name",
        )
        filter_fields = ("name",)
        interfaces = (relay.Node,)


class ExportNode(DjangoObjectType):
    class Meta:
        model = Export
        fields = ("id", "name", "description", "created", "updated")
        filter_fields = []
        interfaces = (relay.Node,)


class PlaceExportNode(DjangoObjectType):
    class Meta:
        model = PlaceExport
        fields = ("export", "significance")
        filter_fields = ("export", "significance")
        interfaces = (relay.Node,)


class PlaceRaceNode(DjangoObjectType):
    class Meta:
        model = PlaceRace
        fields = (
            "race",
            "percent",
            "notes",
        )
        filter_fields = ("percent",)
        interfaces = (relay.Node,)


class PlaceAssociation(DjangoObjectType):
    class Meta:
        model = PlaceAssociation
        fields = (
            "association",
            "notes",
        )
        filter_fields = []
        interfaces = (relay.Node,)


class PlaceNode(DjangoObjectType):
    parent = relay.Node.Field(lambda: PlaceNode)
    exports = DjangoFilterConnectionField(PlaceExportNode)
    common_races = DjangoFilterConnectionField(PlaceRaceNode)
    associations = DjangoFilterConnectionField(PlaceAssociation)

    class Meta:
        model = Place
        fields = (
            "id",
            "name",
            "description",
            "created",
            "updated",
            "place_type",
            "parent",
            "population",
            "exports",
            "common_races",
            "associations",
        )
        filter_fields = [
            "name",
            "description",
            "created",
            "updated",
        ]
        interfaces = (relay.Node,)


# class ItemNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Item


# class ArtifactNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Artifact


# class ArmorNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Armor


# class EquipmentNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Equipment


# class WeaponNode(ItemNodeBase, DjangoObjectType):
#     class Meta(ItemNodeBase.Meta):
#         model = Weapon
