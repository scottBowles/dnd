from django.db import models
from django.contrib.auth.models import User


class Character(models.Model):
    class Alignment(models.TextChoices):
        LAWFUL_GOOD = "LG", "Lawful Good"
        NEUTRAL_GOOD = "NG", "Neutral Good"
        CHAOTIC_GOOD = "CG", "Chaotic Good"
        LAWFUL_NEUTRAL = "LN", "Lawful Neutral"
        TRUE_NEUTRAL = "N", "True Neutral"
        CHAOTIC_NEUTRAL = "CN", "Chaotic Neutral"
        LAWFUL_EVIL = "LE", "Lawful Evil"
        NEUTRAL_EVIL = "NE", "Neutral Evil"
        CHAOTIC_EVIL = "CE", "Chaotic Evil"

    name = models.CharField(max_length=200, null=True, blank=True)
    alignment = models.CharField(
        max_length=2, choices=Alignment.choices, null=True, blank=True
    )
    character_class = models.CharField(
        max_length=200, null=True, blank=True
    )  # many to many? include levels?
    level = models.IntegerField(default=1)  # per character class?
    background = models.CharField(max_length=200, null=True, blank=True)  # fk
    race = models.CharField(max_length=200, null=True, blank=True)  # fk
    experience_points = models.IntegerField(default=1)
    hit_points = models.IntegerField(default=0)  # calculated? probably not
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    def armor_class(self):
        # TODO: flesh this out
        # return 10 + self.dexterity()
        pass

    def initiative(self):
        pass

    def speed(self):
        pass
