from place.models.place import PlaceAssociation
from .models import (
    Place,
    Star,
    Planet,
    Moon,
    Region,
    Town,
    District,
    Location,
    Export,
    PlaceExport,
)
from nucleus.utils import RelayPrimaryKeyRelatedField, RelayModelSerializer

"""
Places are held on one table with proxy models for different place types.
Serializers and schemas should take care of exposing the correct fields for
each type.
"""


class ExportSerializer(RelayModelSerializer):
    class Meta:
        model = Export
        fields = (
            "id",
            "name",
            "description",
        )


class PlaceExportSerializer(RelayModelSerializer):
    place = RelayPrimaryKeyRelatedField(
        queryset=Place.objects.all(),
        default=None,
        # default set for use in place mutations, where place is added in PlaceSerializer's methods
        # see:
        # https://github.com/encode/django-rest-framework/issues/4456
        # and
        # https://www.django-rest-framework.org/api-guide/validators/#uniquetogethervalidator
    )

    class Meta:
        model = PlaceExport
        fields = ("significance", "export", "place")


class PlaceAssociationSerializer(RelayModelSerializer):
    place = RelayPrimaryKeyRelatedField(
        queryset=Place.objects.all(),
        default=None,
        # default set for use in place mutations, where place is added in PlaceSerializer's methods
        # see:
        # https://github.com/encode/django-rest-framework/issues/4456
        # and
        # https://www.django-rest-framework.org/api-guide/validators/#uniquetogethervalidator
    )

    class Meta:
        model = PlaceAssociation
        fields = ("notes", "association", "place")


class PlaceSerializer(RelayModelSerializer):
    exports = PlaceExportSerializer(many=True, required=False)
    associations = PlaceAssociationSerializer(many=True, required=False)

    class Meta:
        model = Place
        fields = (
            "id",
            "name",
            "description",
            "image_id",
            "thumbnail_id",
            "created",
            "updated",
            "place_type",
            "parent",
            "population",
            "exports",
            "common_races",
            "associations",
        )

    def create(self, validated_data):
        exports_data = validated_data.pop("exports", [])
        associations_data = validated_data.pop("associations", [])
        place = super().create(validated_data)
        for export_data in exports_data:
            export_data["place"] = place
            PlaceExport.objects.create(**export_data)
        for association_data in associations_data:
            association_data["place"] = place
            PlaceAssociation.objects.create(**association_data)
        return place


class StarSerializer(PlaceSerializer):
    class Meta(PlaceSerializer):
        model = Star


class PlanetSerializer(RelayModelSerializer):
    class Meta:
        model = Planet


class MoonSerializer(RelayModelSerializer):
    class Meta:
        model = Moon


class RegionSerializer(RelayModelSerializer):
    class Meta:
        model = Region


class TownSerializer(RelayModelSerializer):
    class Meta:
        model = Town


class DistrictSerializer(RelayModelSerializer):
    class Meta:
        model = District


class LocationSerializer(RelayModelSerializer):
    class Meta:
        model = Location
