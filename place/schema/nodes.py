from django.db.models import Prefetch
import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from association.schema import AssociationNode
from nucleus.utils import login_or_queryset_none
from race.schema.nodes import RaceNode
from ..models import Place, PlaceExport, Export, PlaceRace, PlaceAssociation


class ExportNode(DjangoObjectType):
    locked_by_self = graphene.Boolean()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = Export
        fields = (
            "id",
            "name",
            "description",
            "created",
            "updated",
            "markdown_notes",
            "lock_user",
            "lock_time",
        )
        filter_fields = []
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class PlaceExportNode(DjangoObjectType):
    significance = graphene.String()

    def resolve_significance(self, info):
        return self.SIGNIFICANCE[self.significance][1]

    class Meta:
        model = PlaceExport
        fields = ("significance", "export", "place")
        filter_fields = []
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class PlaceAssociationConnection(relay.Connection):
    class Meta:
        node = AssociationNode

    class Edge:
        notes = graphene.String()

        def resolve_notes(self, info):
            try:
                return next(
                    place_association.notes
                    for place_association in self.node.place_associations
                    if place_association.association == self.node
                )
            except StopIteration:
                return None


class ExportConnection(relay.Connection):
    class Meta:
        node = ExportNode

    class Edge:
        significance = graphene.String()

        def resolve_significance(self, info):
            try:
                return next(
                    place_export.get_significance_display()
                    for place_export in self.node.place_exports
                    if place_export.export == self.node
                )
            except StopIteration:
                return None


class RaceConnection(relay.Connection):
    class Meta:
        node = RaceNode

    class Edge:
        percent = graphene.Float()
        notes = graphene.String()

        @property
        def place_race(self):
            try:
                return next(
                    place_race
                    for place_race in self.node.place_races
                    if place_race.race == self.node
                )
            except StopIteration:
                return None

        def resolve_percent(self, info):
            return self.place_race.percent if self.place_race is not None else None

        def resolve_notes(self, info):
            return self.place_race.notes if self.place_race is not None else None


class PlaceNode(DjangoObjectType):
    parent = graphene.Field(lambda: PlaceNode)
    exports = relay.ConnectionField(ExportConnection)
    common_races = relay.ConnectionField(RaceConnection)
    associations = relay.ConnectionField(PlaceAssociationConnection)
    locked_by_self = graphene.Boolean()
    place_type_display = graphene.String()

    def resolve_associations(self, info, **kwargs):
        qs = PlaceAssociation.objects.filter(place=self)
        return self.associations.prefetch_related(
            Prefetch("placeassociation_set", queryset=qs, to_attr="place_associations")
        )

    def resolve_exports(self, info, **kwargs):
        qs = PlaceExport.objects.filter(place=self)
        return self.exports.prefetch_related(
            Prefetch("placeexport_set", queryset=qs, to_attr="place_exports")
        )

    def resolve_common_races(self, info, **kwargs):
        qs = PlaceRace.objects.filter(place=self)
        return self.common_races.prefetch_related(
            Prefetch("placerace_set", queryset=qs, to_attr="place_races")
        )

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    def resolve_place_type_display(self, info, **kwargs):
        return self.get_place_type_display()

    class Meta:
        model = Place
        fields = (
            "id",
            "name",
            "description",
            "image_ids",
            "thumbnail_id",
            "created",
            "updated",
            "place_type",
            "place_type_display",
            "parent",
            "children",
            "population",
            "exports",
            "common_races",
            "associations",
            "markdown_notes",
            "lock_user",
            "lock_time",
            "logs",
        )
        filter_fields = [
            "place_type",
            "name",
            "description",
            "created",
            "updated",
        ]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset
