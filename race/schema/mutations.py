import graphene

from nucleus.utils import RelayCUD
from ..models import AbilityScoreIncrease, Trait, Race

from ..serializers import (
    RaceSerializer,
    AbilityScoreIncreaseSerializer,
    TraitSerializer,
)
from .nodes import AbilityScoreIncreaseNode, TraitNode, RaceNode
from character.models.models import ABILITIES


class AbilityScoreIncreaseInput(graphene.InputObjectType):
    ability_score = graphene.String(required=True)
    increase = graphene.Int(required=True)


class AbilityScoreIncreaseCUD(RelayCUD):
    field = "abilityScoreIncrease"
    Node = AbilityScoreIncreaseNode
    model = AbilityScoreIncrease
    serializer_class = AbilityScoreIncreaseSerializer
    actions = ("create",)

    class Input:
        ability_score = graphene.String(required=True)
        increase = graphene.Int(required=True)


class TraitCUD(RelayCUD):
    field = "trait"
    Node = TraitNode
    model = Trait
    serializer_class = TraitSerializer

    class Input:
        name = graphene.String(required=True)
        description = graphene.String()


class RaceCUD(RelayCUD):
    field = "race"
    Node = RaceNode
    model = Race
    serializer_class = RaceSerializer

    class Input:
        name = graphene.String(required=True)
        description = graphene.String()
        image_id = graphene.String()
        thumbnail_id = graphene.String()

        age_of_adulthood = graphene.Int()
        life_expectancy = graphene.Int()
        # alignment = models.CharField(
        #     max_length=2, choices=ALIGNMENTS, null=True, blank=True
        # )
        alignment = graphene.String()
        # size = models.CharField(max_length=10, choices=SIZES, null=True, blank=True)
        size = graphene.String()
        speed = graphene.Int()
        # ability_score_increases = graphene.List(graphene.String)
        languages = graphene.List(graphene.String)
        traits = graphene.List(graphene.String)
        subraces = graphene.List(graphene.String)
        base_race = graphene.String()


# class RaceInput(graphene.InputObjectType):
#     """
#     This should eventually be constructed in the Race app and
#     imported from there
#     """

#     name = graphene.String()


# class PlaceExportInput(graphene.InputObjectType):
#     export = graphene.String()
#     significance = graphene.Int()


# class PlaceRaceInput(graphene.InputObjectType):
#     race = RaceInput()
#     percent = graphene.Float()
#     notes = graphene.String()


# class PlaceAssociationInput(graphene.InputObjectType):
#     association = graphene.String()
#     notes = graphene.String()


# class ExportInput:
#     id = graphene.ID()
#     name = graphene.String()
#     description = graphene.String()


# class PlaceInput:
#     name = graphene.String()
#     description = graphene.String()
#     place_type = graphene.String()
#     population = graphene.Int()
#     associations = graphene.List(PlaceAssociationInput)
#     races = graphene.List(PlaceRaceInput)
#     exports = graphene.List(PlaceExportInput)
#     parent = graphene.UUID()


# class PlaceCUD(RelayCUD):
#     field = "place"
#     Node = PlaceNode
#     model = Place
#     serializer_class = PlaceSerializer

#     class Input:
#         name = graphene.String()
#         description = graphene.String()
#         place_type = graphene.String()
#         population = graphene.Int()
#         associations = graphene.List(PlaceAssociationInput)
#         races = graphene.List(PlaceRaceInput)
#         exports = graphene.List(PlaceExportInput)
#         parent = graphene.UUID()


# class ExportCUD(RelayCUD):
#     field = "export"
#     Node = ExportNode
#     model = Export
#     serializer_class = ExportSerializer

#     class Input:
#         name = graphene.String()
#         description = graphene.String()


# class PlaceExportCUD(RelayCUD):
#     field = "place_export"
#     Node = PlaceExportNode
#     model = PlaceExport
#     serializer_class = PlaceExportSerializer

#     class Input:
#         place = graphene.String()
#         export = graphene.String()
#         significance = graphene.Int()

#     class IdentifyingInput:
#         place = graphene.String()
#         export = graphene.String()

#     def get_instance(self, info, input):
#         place_id = from_global_id(input["place"])[1]
#         export_id = from_global_id(input["export"])[1]
#         return self.model.objects.get(place__id=place_id, export__id=export_id)


AbilityScoreIncreaseMutations = AbilityScoreIncreaseCUD().get_mutation_class()
TraitMutations = TraitCUD().get_mutation_class()
RaceMutations = RaceCUD().get_mutation_class()


class Mutation(
    AbilityScoreIncreaseMutations,
    TraitMutations,
    RaceMutations,
    graphene.ObjectType,
):
    pass
