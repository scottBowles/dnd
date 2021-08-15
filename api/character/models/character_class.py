from django.db import models
from .mixins import HitDieMixin

STRENGTH = "STR"
DEXTERITY = "DEX"
CONSTITUTION = "CON"
INTELLIGENCE = "INT"
WISDOM = "WIS"
CHARISMA = "CHA"
SAVING_THROW_MAJOR = [
    (DEXTERITY, "dexterity"),
    (CONSTITUTION, "constitution"),
    (WISDOM, "wisdom"),
]
SAVING_THROW_MINOR = [
    (STRENGTH, "strength"),
    (INTELLIGENCE, "intelligence"),
    (CHARISMA, "charisma"),
]


class CharacterClass(HitDieMixin):
    # TODO: need some way of handling options
    class Meta:
        verbose_name_plural = "character classes"

    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField()

    skill_number = models.PositiveIntegerField(default=0)
    multiclass_skill_number = models.PositiveIntegerField(default=0)
    equipment_choices = models.TextField()
    major_saving_throw = models.CharField(choices=SAVING_THROW_MAJOR, max_length=3)
    minor_saving_throw = models.CharField(choices=SAVING_THROW_MINOR, max_length=3)
    proficient_light_armor = models.BooleanField(default=False)
    proficient_heavy_armor = models.BooleanField(default=False)
    proficient_shields = models.BooleanField(default=False)
    proficient_martial_weapons = models.BooleanField(default=False)
    proficient_simple_weapons = models.BooleanField(default=False)
    proficient_other = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
