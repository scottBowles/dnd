from django.db import models
from graphql_relay import to_global_id

from character.models.models import Language, ABILITIES, ALIGNMENTS, SIZES
from nucleus.models import Entity


class AbilityScoreIncrease(models.Model):
    ability_score = models.CharField(
        max_length=12,
        choices=ABILITIES,
    )
    increase = models.IntegerField()

    class Meta:
        unique_together = (("ability_score", "increase"),)


class Trait(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)


class Race(Entity):
    ability_score_increases = models.ManyToManyField(AbilityScoreIncrease, blank=True)
    age_of_adulthood = models.PositiveIntegerField(null=True, blank=True)
    life_expectancy = models.PositiveIntegerField(null=True, blank=True)
    alignment = models.CharField(
        max_length=2, choices=ALIGNMENTS, null=True, blank=True
    )
    size = models.CharField(max_length=10, choices=SIZES, null=True, blank=True)
    speed = models.PositiveIntegerField(null=True, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    # names? trouble is different races have different configurations
    traits = models.ManyToManyField(Trait, blank=True)
    # proficiencies? maybe just traits here, b/c some are options, etc.
    base_race = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subraces"
    )
    related_races = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
    )

    def global_id(self):
        return to_global_id("RaceNode", self.id)

    def __str__(self):
        return self.name
