import math

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.aggregates import Sum
from .character_class import CharacterClass
from .mixins import HitDieMixin
from equipment.models import Equipment, Weapon, Armor
from race.models import Race
from .models import (
    ABILITIES,
    ALIGNMENTS,
    SIZES,
    Background,
    Feat,
    Feature,
    Language,
    Proficiency,
    Skill,
    Tool,
)


class AbilityScoreArrayMixin(models.Model):
    strength = models.PositiveIntegerField(default=10)
    dexterity = models.PositiveIntegerField(default=10)
    constitution = models.PositiveIntegerField(default=10)
    intelligence = models.PositiveIntegerField(default=10)
    wisdom = models.PositiveIntegerField(default=10)
    charisma = models.PositiveIntegerField(default=10)

    def get_ability_modifier(self, ability):
        return getattr(self, ability.lower()) // 2 - 5

    @property
    def strength_save(self):
        return self.get_ability_modifier("strength") + self.proficiency_bonus

    @property
    def dexterity_save(self):
        return self.get_ability_modifier("dexterity") + self.proficiency_bonus

    @property
    def constitution_save(self):
        return self.get_ability_modifier("constitution") + self.proficiency_bonus

    @property
    def intelligence_save(self):
        return self.get_ability_modifier("intelligence") + self.proficiency_bonus

    @property
    def wisdom_save(self):
        return self.get_ability_modifier("wisdom") + self.proficiency_bonus

    @property
    def charisma_save(self):
        return self.get_ability_modifier("charisma") + self.proficiency_bonus

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
    @admin.display(description="Total Cash on Hand (cp)")
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


class HitPointsMixin(models.Model):
    max_hit_points = models.PositiveIntegerField(default=1)
    temporary_hit_points = models.IntegerField(default=0)
    damage_taken = models.PositiveIntegerField(default=0)

    @property
    @admin.display(description="Current Hit Points")
    def hit_points_current(self):
        return self.max_hit_points + self.temporary_hit_points - self.damage_taken

    class Meta:
        abstract = True


class Character(
    AbilityScoreArrayMixin,
    HitDieMixin,
    HitPointsMixin,
    MoneyHolderMixin,
):

    # NAME BLOCK
    name = models.CharField(max_length=200, null=True, blank=True)

    # CHARACTER INFO BLOCK
    # classes and levels through fk
    @property
    def total_level(self):
        return self.classandlevel_set.aggregate(Sum("level"))["level__sum"] or 0

    background = models.ForeignKey(
        Background, null=True, blank=True, on_delete=models.SET_NULL
    )
    player_name = models.CharField(max_length=200, null=True, blank=True)
    race = models.ForeignKey(Race, null=True, blank=True, on_delete=models.SET_NULL)
    alignment = models.CharField(
        max_length=2, choices=ALIGNMENTS, null=True, blank=True
    )
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
    features_and_traits = models.ManyToManyField(Feature, related_name="characters")

    # ABILITY SCORE BLOCK
    # ability scores through mixin

    # INSPIRATION & PROFICIENCY BONUS BLOCK
    inspiration = models.BooleanField(default=False)

    @property
    def proficiency_bonus(self):
        return math.ceil((self.total_level / 4) + 1) if self.total_level else 0

    proficiencies = models.ManyToManyField(Proficiency, related_name="characters")

    def is_proficient(self, name, proficiency_type=None):
        if proficiency_type:
            return self.proficiencies.filter(
                name=name, proficiency_type=proficiency_type
            ).exists()
        else:
            return self.proficiencies.filter(name=name).exists()

    def get_save_modifier(self, ability):
        prof_bonus = (
            self.proficiency_bonus
            if self.is_proficient(ability, Proficiency.ABILITY)
            else 0
        )
        ability_modifier = self.get_ability_modifier(ability)
        return prof_bonus + ability_modifier

    @property
    @admin.display(description="Languages (select as proficiencies)")
    def languages_proficient(self):
        language_proficiencies = self.proficiencies.filter(
            proficiency_type=Proficiency.LANGUAGE
        )
        names = language_proficiencies.values_list("name", flat=True)
        return list(Language.objects.filter(name__in=names))

    # SKILLS BLOCK
    def get_skill_modifier(self, skill_name):
        skill = Skill.objects.get(name=skill_name)
        related_ability = skill.related_ability
        ability_modifier = self.get_ability_modifier(related_ability)
        prof_bonus = (
            self.proficiency_bonus
            if self.is_proficient(skill_name, Proficiency.SKILL)
            else 0
        )
        return ability_modifier + prof_bonus

    # PASSIVE WISDOM & PASSIVE INTELLIGENCE BLOCK
    passive_wisdom = models.PositiveIntegerField(default=10)
    passive_wisdom.help_text = (
        "10 + wisdom mod + bonuses (including perception proficiency bonus)"
    )
    passive_intelligence = models.PositiveIntegerField(default=10)
    passive_intelligence.help_text = (
        "10 + intelligence mod + bonuses (including investigation proficiency bonus)"
    )

    # MONEY BLOCK
    # through mixin

    # EQUIPMENT BLOCK
    equipment = models.ManyToManyField(
        Equipment, through="InventoryEquipment", blank=True
    )

    tool = models.ManyToManyField(Tool, through="InventoryTool", blank=True)

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

    # OTHER
    size = models.CharField(max_length=10, choices=SIZES, null=True, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name or ""


class NameTextCharacterField(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")

    class Meta:
        abstract = True


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


class InventoryTool(InventoryItem):
    gear = models.ForeignKey(Tool, on_delete=models.CASCADE)


class Attack(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE)
    attack_bonus = models.IntegerField()
    damage = models.CharField(max_length=100)
    damage_type = models.CharField(max_length=100, default="")
    range = models.PositiveIntegerField(default=0)
    properties = models.TextField(default="")
    ability_options = ArrayField(
        models.CharField(max_length=12, choices=ABILITIES), default=list
    )
    ability_options.help_text = "Comma separated ability scores. Usually 'strength' or 'dexterity'. With finesse: 'strength, dexterity'."
    proficiency_needed = models.ForeignKey(
        Proficiency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"proficiency_type": Proficiency.WEAPON},
    )
    proficiency_needed.help_text = (
        "E.g., 'martial weapons'. May have to create the needed proficiency."
    )

    @property
    @admin.display(description="Ability Modifiers")
    def ability_modifiers(self):
        return [
            (
                ability,
                self.character.get_ability_modifier(ability),
            )
            for ability in self.ability_options
        ]
