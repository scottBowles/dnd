from django.db import models
from graphql_relay import to_global_id

from nucleus.models import Entity
from race.models import Race
from association.models import Association


def validate_none():
    """
    This is currently here because it exists in a migration. Remove when able.
    """
    pass


class Export(Entity):
    pass


class PlaceExport(models.Model):
    MAJOR = 0
    MINOR = 1
    SIGNIFICANCE = [
        (MAJOR, "Major"),
        (MINOR, "Minor"),
    ]

    place = models.ForeignKey("Place", on_delete=models.CASCADE)
    export = models.ForeignKey(Export, on_delete=models.CASCADE)
    significance = models.IntegerField(choices=SIGNIFICANCE, default=MAJOR)

    def __str__(self):
        return f"{self.place} - {self.export}"

    class Meta:
        unique_together = ("place", "export")


class PlaceRace(models.Model):
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    place = models.ForeignKey("Place", on_delete=models.CASCADE)
    percent = models.FloatField()
    notes = models.TextField()

    def __str__(self):
        return f"{self.place} - {self.race}"


class PlaceAssociation(models.Model):
    place = models.ForeignKey("Place", on_delete=models.CASCADE)
    association = models.ForeignKey(Association, on_delete=models.CASCADE)
    notes = models.TextField()

    def __str__(self):
        return f"{self.place} - {self.association}"


class Place(Entity):
    STAR = "Star"
    PLANET = "Planet"
    MOON = "Moon"
    REGION = "Region"
    TOWN = "Town"
    DISTRICT = "District"
    LOCATION = "Location"

    PLACE_TYPES = [
        (STAR, "Star"),
        (PLANET, "Planet"),
        (MOON, "Moon"),
        (REGION, "Region"),
        (TOWN, "Town"),
        (DISTRICT, "District"),
        (LOCATION, "Location"),
    ]
    place_type = models.CharField(
        max_length=8, choices=PLACE_TYPES, null=True, blank=True
    )

    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )

    population = models.IntegerField(default=0)
    exports = models.ManyToManyField(Export, through="PlaceExport")
    common_races = models.ManyToManyField(Race, through="PlaceRace")
    associations = models.ManyToManyField(Association, through="PlaceAssociation")

    def global_id(self):
        return to_global_id("PlaceNode", self.id)

    def __str__(self):
        return self.name


class StarManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.STAR)


class Star(Place):
    objects = StarManager()

    class Meta:
        proxy = True


class PlanetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.PLANET)


class Planet(Place):
    objects = PlanetManager()

    class Meta:
        proxy = True


class MoonManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.MOON)


class Moon(Place):
    objects = MoonManager()

    class Meta:
        proxy = True


class RegionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.REGION)


class Region(Place):
    objects = RegionManager()

    class Meta:
        proxy = True


class TownManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.TOWN)


class Town(Place):
    objects = TownManager()

    class Meta:
        proxy = True


class DistrictManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.DISTRICT)


class District(Place):
    objects = DistrictManager()

    class Meta:
        proxy = True


class LocationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(place_type=Place.LOCATION)


class Location(Place):
    objects = LocationManager()

    class Meta:
        proxy = True
