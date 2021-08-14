from django.db import models

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

D4 = "4"
D6 = "6"
D8 = "8"
D10 = "10"
D12 = "12"
D20 = "20"

HIT_DIE_CHOICES = [
    (D4, "d4"),
    (D6, "d6"),
    (D8, "d8"),
    (D10, "d10"),
    (D12, "d12"),
    (D20, "d20"),
]


class CharacterClass(models.Model):
    # TODO: need some way of handling options
    class Meta:
        verbose_name_plural = "character classes"

    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField()
    hit_die = models.CharField(max_length=2, choices=HIT_DIE_CHOICES)

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
