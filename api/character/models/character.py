import math

from django.db import models
from django.contrib.auth.models import User
from django.db.models.aggregates import Sum
from .character_class import CharacterClass
from .mixins import HitDieMixin
from equipment.models import Equipment, Weapon, Armor

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


class Skill(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    related_ability = models.CharField(max_length=12, choices=ABILITIES)
    custom = models.BooleanField(default=True)


class Language(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)


class Tool(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)


class Feat(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(default="", blank=True)
    custom = models.BooleanField(default=True)


class AbilityScoreArrayMixin(models.Model):
    strength = models.PositiveIntegerField(default=10)
    dexterity = models.PositiveIntegerField(default=10)
    constitution = models.PositiveIntegerField(default=10)
    intelligence = models.PositiveIntegerField(default=10)
    wisdom = models.PositiveIntegerField(default=10)
    charisma = models.PositiveIntegerField(default=10)

    @staticmethod
    def _get_modifier(score):
        return score // 2 - 5 if type(score) is int else score

    @property
    def strength_modifier(self):
        return Character._get_modifier(self.strength)

    @property
    def dexterity_modifier(self):
        return Character._get_modifier(self.dexterity)

    @property
    def constitution_modifier(self):
        return Character._get_modifier(self.constitution)

    @property
    def intelligence_modifier(self):
        return Character._get_modifier(self.intelligence)

    @property
    def wisdom_modifier(self):
        return Character._get_modifier(self.wisdom)

    @property
    def charisma_modifier(self):
        return Character._get_modifier(self.charisma)

    class Meta:
        # abstract for now, but if I want to be able to query all ability score arrays, should instead use multi-table inheritance (https://docs.djangoproject.com/en/dev/topics/db/models/#id6)
        abstract = True


class MoneyHolderMixin(models.Model):
    copper_pieces = models.PositiveIntegerField(default=0)
    silver_pieces = models.PositiveIntegerField(default=0)
    electrum_pieces = models.PositiveIntegerField(default=0)
    gold_pieces = models.PositiveIntegerField(default=0)
    platinum_pieces = models.PositiveIntegerField(default=0)

    @property
    def total_cash_on_hand(self):
        return (
            self.copper_pieces
            + self.silver_pieces * 10
            + self.electrum_pieces * 50
            + self.gold_pieces * 100
            + self.platinum_pieces * 1000
        )

    class Meta:
        # abstract for now, but if I want to be able to query all MoneyHolders, should instead use multi-table inheritance (https://docs.djangoproject.com/en/dev/topics/db/models/#id6)
        abstract = True


class AlignmentMixin(models.Model):
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

    alignment = models.CharField(
        max_length=2, choices=Alignment.choices, null=True, blank=True
    )

    class Meta:
        abstract = True


class HitPointsMixin(models.Model):
    max_hit_points = models.PositiveIntegerField(default=1)
    temporary_hit_points = models.IntegerField(default=0)
    damage_taken = models.PositiveIntegerField(default=0)

    @property
    def hit_points_current(self):
        return self.max_hit_points + self.temporary_hit_points - self.damage_taken

    class Meta:
        abstract = True


class EquipmentFromInitialClass(models.Model):
    # probably not using this
    # need different for weapon, armor, etc.?
    class Meta:
        verbose_name_plural = "equipment from initial class"

    initial_class = models.ForeignKey(
        CharacterClass, null=True, on_delete=models.SET_NULL
    )
    # equipment = many to many
    # equipment_choices = text field -- can I use multiple for a multiple?


class Character(
    AbilityScoreArrayMixin,
    AlignmentMixin,
    HitDieMixin,
    HitPointsMixin,
    MoneyHolderMixin,
):

    # NAME BLOCK
    name = models.CharField(max_length=200, null=True, blank=True)

    # CHARACTER INFO BLOCK
    def class_and_level(self):
        return (c for c in self.classandlevel_set.all())

    @property
    def total_level(self):
        return self.classandlevel_set.aggregate(Sum("level"))["level__sum"]

    # TODO: use fk
    background = models.CharField(max_length=200, null=True, blank=True)
    player_name = models.CharField(max_length=200, null=True, blank=True)
    # TODO: use fk
    race = models.CharField(max_length=200, null=True, blank=True)
    # alignment through mixin
    experience_points = models.PositiveIntegerField(default=0)

    # CENTER TOP BLOCK
    armor_class = models.PositiveIntegerField(default=10)
    armor_class.help_text = "10 + dex mod + bonuses from armor, shields, spells, natural ac, class abilities, feats, magical items, etc."
    initiative = models.PositiveIntegerField(default=0)
    initiative.help_text = "Equal to dex mod unless you have a feat or similar. If you're not sure, it's your dex mod."
    speed = models.PositiveIntegerField(default=0)  # choices?
    speed.help_text = "Usually comes from your race"
    # hp through mixin
    # hit die through mixin
    num_hit_dice = models.PositiveIntegerField(default=1)
    num_hit_dice.help_text = "Almost certainly the same as your character level"
    death_save_successes = models.PositiveIntegerField(default=0)
    death_save_failures = models.PositiveIntegerField(default=0)

    # TRAITS BLOCK
    def personality_traits(self):
        return self.personalitytrait_set.all()

    def ideals(self):
        return self.ideal_set.all()

    def bonds(self):
        return self.bond_set.all()

    def flaws(self):
        return self.flaw_set.all()

    # FEATURES AND TRAITS BLOCK
    def features_and_traits(self):
        return self.featureandtrait_set.all()

    # ABILITY SCORE BLOCK
    # ability scores through mixin

    # INSPIRATION & PROFICIENCY BONUS BLOCK
    inspiration = models.BooleanField(default=False)

    @property
    def proficiency_bonus(self):
        return math.ceil((self.total_level / 4) + 1)

    # SAVING THROW BLOCK
    proficient_strength = models.BooleanField(default=False)
    proficient_dexterity = models.BooleanField(default=False)
    proficient_constitution = models.BooleanField(default=False)
    proficient_intelligence = models.BooleanField(default=False)
    proficient_wisdom = models.BooleanField(default=False)
    proficient_charisma = models.BooleanField(default=False)

    @property
    def save_modifier(self, ability):
        is_proficient = getattr(self, "proficient_" + ability)
        prof_bonus = self.proficiency_bonus if is_proficient else 0
        ability_score = self[ability]
        ability_mod = self._get_modifier(ability_score)
        return prof_bonus + ability_mod

    # SKILLS BLOCK
    skills = models.ManyToManyField(Skill, through="CharacterSkill")

    # PASSIVE WISDOM & PASSIVE INTELLIGENCE BLOCK
    passive_wisdom = models.PositiveIntegerField(default=10)
    passive_wisdom.help_text = (
        "10 + wisdom mod + bonuses (including perception proficiency bonus)"
    )
    passive_intelligence = models.PositiveIntegerField(default=10)
    passive_intelligence.help_text = (
        "10 + intelligence mod + bonuses (including investigation proficiency bonus)"
    )

    # OTHER PROFICIENCIES AND LANGUAGES BLOCK
    # Armor Proficiencies
    proficient_light_armor = models.BooleanField(default=False)
    proficient_medium_armor = models.BooleanField(default=False)
    proficient_heavy_armor = models.BooleanField(default=False)
    proficient_shields = models.BooleanField(default=False)

    # Weapon Proficiencies
    proficient_simple = models.BooleanField(default=False)
    proficient_martial = models.BooleanField(default=False)

    # Tool Proficiencies
    proficient_tools = models.ManyToManyField(Tool, blank=True)

    # Language Proficiencies
    proficient_languages = models.ManyToManyField(Language, blank=True)

    # Other Proficiencies
    proficient_other = models.TextField(blank=True, null=True)

    # MONEY BLOCK
    # through mixin

    # EQUIPMENT BLOCK
    equipment = models.ManyToManyField(
        Equipment, through="InventoryEquipment", blank=True
    )

    # SPELLCASTING BLOCK
    # TODO

    # FEAT BLOCK
    feats = models.ManyToManyField(Feat, blank=True)

    # WEAPONS BLOCK
    weapons = models.ManyToManyField(Weapon, through="InventoryWeapon", blank=True)

    # ARMOR BLOCK
    armor = models.ManyToManyField(Armor, through="InventoryArmor", blank=True)

    # ATTACKS BLOCK
    # TODO

    equipment_from_initial_class = models.ForeignKey(
        EquipmentFromInitialClass, null=True, blank=True, on_delete=models.SET_NULL
    )  # do we care about this? do we really need to know where it comes from? over-complicating?

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class NameTextCharacterField(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")


class Bond(NameTextCharacterField):
    type = "bond"


class PersonalityTrait(NameTextCharacterField):
    type = "personalitytrait"


class Ideal(NameTextCharacterField):
    type = "ideal"


class Flaw(NameTextCharacterField):
    type = "flaw"


class ClassAndLevel(models.Model):
    """Mapping table for tracking a character's class and level in that class."""

    class Meta:
        verbose_name_plural = "classes and levels"

    character_class = models.ForeignKey(to=CharacterClass, on_delete=models.CASCADE)
    level = models.PositiveIntegerField()
    character = models.ForeignKey(to=Character, on_delete=models.CASCADE)


class CharacterSkill(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficient = models.BooleanField(default=False)

    @property
    def modifier(self):
        prof_bonus = self.character.proficient_bonus if self.proficient else 0
        ability = self.skill.related_ability
        ability_modifier = getattr(self.character, "{}_modifier".format(ability))
        return prof_bonus + ability_modifier


class FeaturesAndTraits(NameTextCharacterField):
    class Meta:
        verbose_name_plural = "features and traits"

    type = "featuresandtraits"


class InventoryItem(models.Model):
    # Not to be used directly
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()


class InventoryArmor(InventoryItem):
    gear = models.ForeignKey(Armor, on_delete=models.CASCADE)


class InventoryWeapon(InventoryItem):
    gear = models.ForeignKey(Weapon, on_delete=models.CASCADE)


class InventoryEquipment(InventoryItem):
    gear = models.ForeignKey(Equipment, on_delete=models.CASCADE)
