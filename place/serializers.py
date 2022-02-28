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
from nucleus.utils import RelayPrimaryKeyRelatedField

"""
Places are held on one table with proxy models for different place types.
Serializers and schemas should take care of exposing the correct fields for
each type.
"""


class PlaceExportSerializer(serializers.ModelSerializer):
    export = RelayPrimaryKeyRelatedField(queryset=Export.objects.all())

    class Meta:
        model = PlaceExport
        fields = ("significance", "export")


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
        exports_data = validated_data.pop("exports", [])
        place = super().create(validated_data)
        for export_data in exports_data:
            PlaceExport.objects.create(place=place, **export_data)
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
