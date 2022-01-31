from django.db import models

from nucleus.models import Entity
from race.models import Race
from association.models import Association


class Export(Entity):
    pass


class PlaceDetails(models.Model):
    population = models.IntegerField(default=0)
    exports = models.ManyToManyField(Export, through="PlaceExport")
    common_races = models.ManyToManyField(Race, through="PlaceRace")
    associations = models.ManyToManyField(Association, through="PlaceAssociation")


class PlaceRace(models.Model):
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    location = models.ForeignKey(PlaceDetails, on_delete=models.CASCADE)
    percent = models.FloatField()
    notes = models.TextField()


class PlaceExport(models.Model):
    MAJOR = 0
    MINOR = 1
    SIGNIFICANCE = [
        (MAJOR, "Major"),
        (MINOR, "Minor"),
    ]

    place = models.ForeignKey(PlaceDetails, on_delete=models.CASCADE)
    export = models.ForeignKey(Export, on_delete=models.CASCADE)
    significance = models.IntegerField(choices=SIGNIFICANCE, default=MAJOR)


class PlaceAssociation(models.Model):
    place = models.ForeignKey(PlaceDetails, on_delete=models.CASCADE)
    association = models.ForeignKey(Association, on_delete=models.CASCADE)
    notes = models.TextField()
