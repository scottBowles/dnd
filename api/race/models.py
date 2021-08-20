from django.db import models


class AbilityScoreIncrease(models.Model):
    from character.models.models import ABILITIES

    ability_score = models.CharField(
        max_length=12,
        choices=ABILITIES,
    )
    increase = models.IntegerField()


class Trait(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()


class Race(models.Model):
    from character.models.models import Language, ALIGNMENTS, SIZES

    name = models.CharField(max_length=255)
    ability_score_increases = models.ManyToManyField(AbilityScoreIncrease, blank=True)
    age_of_adulthood = models.PositiveIntegerField(null=True, blank=True)
    life_expectency = models.PositiveIntegerField(null=True, blank=True)
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
        "self", null=True, blank=True, on_delete=models.CASCADE
    )

    @property
    def subraces(self, obj):
        return Race.objects.filter(base_race=obj.pk)
