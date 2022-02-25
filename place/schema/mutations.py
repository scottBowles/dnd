import graphene

from nucleus.utils import RelayCUD
from ..models import Place
from ..serializers import PlaceSerializer
from .nodes import PlaceNode
from association.schema import AssociationInput

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


class ExportInput(graphene.InputObjectType):
    id = graphene.ID()
    name = graphene.String()
    description = graphene.String()


class PlaceExportInput(graphene.InputObjectType):
    export = graphene.String()
    significance = graphene.Int()


class PlaceRaceInput(graphene.InputObjectType):
    race = RaceInput()
    percent = graphene.Float()
    notes = graphene.String()


class PlaceAssociationInput(graphene.InputObjectType):
    association = AssociationInput()
    notes = graphene.String()
    # things = graphene.ConnectionField


class Input:
    name = graphene.String()
    description = graphene.String()
    place_type = graphene.String()
    population = graphene.Int()
    associations = graphene.List(PlaceAssociationInput)
    races = graphene.List(PlaceRaceInput)
    exports = graphene.List(PlaceExportInput)
    parent = graphene.UUID()


PlaceMutations = RelayCUD(
    "place", PlaceNode, Input, Place, PlaceSerializer
).get_mutation_class()


class Mutation(
    PlaceMutations,
    graphene.ObjectType,
):
    pass
