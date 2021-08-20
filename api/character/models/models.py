from django.db import models

STRENGTH = "strength"
DEXTERITY = "dexterity"
CONSTITUTION = "constitution"
INTELLIGENCE = "intelligence"
WISDOM = "wisdom"
CHARISMA = "charisma"
ABILITIES = (
    (STRENGTH, "Strength"),
    (DEXTERITY, "Dexterity"),
    (CONSTITUTION, "Constitution"),
    (INTELLIGENCE, "Intelligence"),
    (WISDOM, "Wisdom"),
    (CHARISMA, "Charisma"),
)

LAWFUL_GOOD = "LG"
NEUTRAL_GOOD = "NG"
CHAOTIC_GOOD = "CG"
LAWFUL_NEUTRAL = "LN"
TRUE_NEUTRAL = "N"
CHAOTIC_NEUTRAL = "CN"
LAWFUL_EVIL = "LE"
NEUTRAL_EVIL = "NE"
CHAOTIC_EVIL = "CE"
ALIGNMENTS = (
    (LAWFUL_GOOD, "Lawful Good"),
    (NEUTRAL_GOOD, "Neutral Good"),
    (CHAOTIC_GOOD, "Chaotic Good"),
    (LAWFUL_NEUTRAL, "Lawful Neutral"),
    (TRUE_NEUTRAL, "True Neutral"),
    (CHAOTIC_NEUTRAL, "Chaotic Neutral"),
    (LAWFUL_EVIL, "Lawful Evil"),
    (NEUTRAL_EVIL, "Neutral Evil"),
    (CHAOTIC_EVIL, "Chaotic Evil"),
)

TINY = "tiny"
SMALL = "small"
MEDIUM = "medium"
LARGE = "large"
HUGE = "huge"
GARGANTUAN = "gargantuan"
SIZES = (
    (TINY, "Tiny"),
    (SMALL, "Small"),
    (MEDIUM, "Medium"),
    (LARGE, "Large"),
    (HUGE, "Huge"),
    (GARGANTUAN, "Gargantuan"),
)


class Feature(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()


class Skill(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    related_ability = models.CharField(max_length=12, choices=ABILITIES)
    custom = models.BooleanField(default=True)


class Script(models.Model):
    name = models.CharField(max_length=255)


class Language(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # typical_speakers = models.ManyToManyField(Race, blank=True)
    script = models.ForeignKey(Script, null=True, blank=True, on_delete=models.SET_NULL)


class Background(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    skill_proficiencies = models.ManyToManyField(Skill, related_name="backgrounds")
    languages = models.ManyToManyField(Language, related_name="backgrounds")
    equipment_options = models.TextField()  # consider connecting this up to equipment
    features = models.ManyToManyField(Feature, related_name="backgrounds")
    suggested_characteristics = models.TextField(blank=True)


class Tool(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)


class Feat(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    custom = models.BooleanField(default=True)
