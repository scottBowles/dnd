import graphene

from nucleus.utils import RelayCUD, ConcurrencyLockActions, ImageMutations
from ..models import Export, Place, PlaceExport
from ..serializers import ExportSerializer, PlaceSerializer, PlaceExportSerializer
from .nodes import ExportNode, PlaceNode, PlaceExportNode
from association.schema import AssociationInput
from graphql_relay import from_global_id

"""
CURRENTLY I HAVE THE CUD MUTATIONS FOR PLACE. NEXT WILL BE THE CUD
ACTIONS FOR THE MANY-TO-MANY RELATIONSHIPS. SHOULD BE ABLE TO PERFORM
THEM BASED ON THE PLACE ID RATHER THAN NEEDING ANY PIVOT TABLE IDS.
POSSIBLY THIS SHOULD BE ACHIEVED BY ASSIGNING THE PLACE ID AS THE
PRIMARY KEY IN THE PIVOT TABLE.

ADDITIONALLY, I SHOULD ADD UNIQUE TOGETHER CONSTRAINTS TO THE PIVOT
TABLES TO ENSURE THAT THERE ARE NO DUPLICATE ASSOCIATIONS.
"""


class RaceInput(graphene.InputObjectType):
    """
    This should eventually be constructed in the Race app and
    imported from there
    """

    name = graphene.String()


class PlaceExportInput(graphene.InputObjectType):
    export = graphene.String()
    significance = graphene.Int()


class PlaceRaceInput(graphene.InputObjectType):
    race = RaceInput()
    percent = graphene.Float()
    notes = graphene.String()


class PlaceAssociationInput(graphene.InputObjectType):
    association = graphene.String()
    notes = graphene.String()


class ExportInput:
    id = graphene.ID()
    name = graphene.String()
    description = graphene.String()
    markdown_notes = graphene.String()


class PlaceInput:
    name = graphene.String()
    description = graphene.String()
    image_ids = graphene.List(graphene.String)
    thumbnail_id = graphene.String()
    place_type = graphene.String()
    population = graphene.Int()
    associations = graphene.List(PlaceAssociationInput)
    races = graphene.List(PlaceRaceInput)
    exports = graphene.List(PlaceExportInput)
    parent = graphene.ID()
    children = graphene.List(graphene.ID)
    markdown_notes = graphene.String()


class PlaceCUD(RelayCUD):
    field = "place"
    Node = PlaceNode
    model = Place
    serializer_class = PlaceSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_ids = graphene.List(graphene.String)
        thumbnail_id = graphene.String()
        place_type = graphene.String()
        population = graphene.Int()
        associations = graphene.List(PlaceAssociationInput)
        races = graphene.List(PlaceRaceInput)
        exports = graphene.List(PlaceExportInput)
        parent = graphene.ID()
        children = graphene.List(graphene.ID)
        markdown_notes = graphene.String()


class ExportCUD(RelayCUD):
    field = "export"
    Node = ExportNode
    model = Export
    serializer_class = ExportSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        markdown_notes = graphene.String()


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


class PlaceConcurrencyLock(ConcurrencyLockActions):
    field = "place"
    Node = PlaceNode
    model = Place


class ExportConcurrencyLock(ConcurrencyLockActions):
    field = "export"
    Node = ExportNode
    model = Export


class PlaceImageMutations(ImageMutations):
    field = "place"
    Node = PlaceNode
    model = Place


class ExportImageMutations(ImageMutations):
    field = "export"
    Node = ExportNode
    model = Export


PlaceCUDMutations = PlaceCUD().get_mutation_class()
PlaceLockMutations = PlaceConcurrencyLock().get_mutation_class()
PlaceImageMutations = PlaceImageMutations().get_mutation_class()
ExportCUDMutations = ExportCUD().get_mutation_class()
ExportLockMutations = ExportConcurrencyLock().get_mutation_class()
ExportImageMutations = ExportImageMutations().get_mutation_class()
# PlaceExportMutations = PlaceExportCUD().get_mutation_class()


class Mutation(
    ExportCUDMutations,
    ExportLockMutations,
    ExportImageMutations,
    PlaceCUDMutations,
    PlaceLockMutations,
    PlaceImageMutations,
    # PlaceExportMutations,
    graphene.ObjectType,
):
    pass
