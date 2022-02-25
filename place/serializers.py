from rest_framework import serializers
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
from graphql_relay import from_global_id, to_global_id

"""
Places are held on one table with proxy models for different place types.
Serializers and schemas should take care of exposing the correct fields for
each type.
"""


# class ExportSerializer(serializers.ModelSerializer):
#     name = serializers.CharField(
#         max_length=255, required=False
#     )  # we don't require here so we can accept an id as input. we will rely instead on the db-level validation from the model to ensure Exports always have a name.

#     class Meta:
#         model = Export
#         fields = ("id", "name", "description", "created", "updated")


class PlaceExportSerializer(serializers.ModelSerializer):
    export = serializers.CharField()  # should be the relay global id of the export

    class Meta:
        model = PlaceExport
        fields = ("significance", "export")

    def create(self, validated_data):
        """
        Create a new PlaceExport instance.
        If an export id is provided, we will expect it to reflect an
        existing export and use that. Otherwise, we will create a new
        export.
        """
        export_global_id = validated_data.pop("export", None)
        export_id = from_global_id(export_global_id)[1]
        export = Export.objects.get(id=export_id)
        validated_data["export"] = export
        place_export = super().create(validated_data)
        place_export.save()
        return place_export


class PlaceSerializer(serializers.ModelSerializer):
    exports = PlaceExportSerializer(many=True, required=False)

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

    def create(self, validated_data):
        exports_data = validated_data.pop("exports", None)
        place = super().create(validated_data)
        if exports_data is not None:
            for export_data in exports_data:
                export_serializer = PlaceExportSerializer(data=export_data)
                export_serializer.is_valid(raise_exception=True)
                export_serializer.save(place=place)

        return place


class StarSerializer(PlaceSerializer):
    class Meta(PlaceSerializer):
        model = Star


class PlanetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planet


class MoonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moon


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region


class TownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Town


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
