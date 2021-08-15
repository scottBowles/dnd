from django.db import models
from django.contrib.auth.models import User
from .character_class import CharacterClass


class AbilityScoreArrayMixin(models.Model):
    # TODO: Remove default, so null value can serve for unknown for creatures we come across?
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


class Character(
    AbilityScoreArrayMixin, AlignmentMixin, HitPointsMixin, MoneyHolderMixin
):
    # Should I have PC and NPC classes that inherit from Character? What is common and not?
    # Should I have characteristics that get recalculated and adjusted on save, or on save from related models, or on creation and on demand only? Worried about calculating too much on the fly.

    name = models.CharField(max_length=200, null=True, blank=True)
    character_class = models.CharField(
        max_length=200, null=True, blank=True
    )  # many to many? include levels? default to some kind of commoner?
    level = models.PositiveIntegerField(default=1)  # sum character class?
    background = models.CharField(max_length=200, null=True, blank=True)  # fk
    race = models.CharField(max_length=200, null=True, blank=True)  # fk
    experience_points = models.PositiveIntegerField(default=0)

    inspiration = models.BooleanField(default=False)
    # equipment = many to many. distinguish by type almost certainly. should have access to custom modifiers.
    # features and traits = many to many. should have access to custom modifiers. many will come from class, race, but will want own model to add custom.
    # attacks and spellcasting -- should come from spellcasting abilities, equipment. all should have unarmed. spellcaster mixin?
    death_save_successes = models.PositiveIntegerField(default=0)  # reset as needed
    death_save_failures = models.PositiveIntegerField(default=0)  # reset as needed

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True
    )  # Create a Player model for this instead, accessing users through that? Seems like a one-to-one facade over user, unless users can have multiple players. Should we let users customize their player information per character (in which case one-to-many)?

    # `Other proficiencies and languages`
    # passive_wisdom

    # Custom modifiers - should there be a custom modifier for each thing or a separate custom modifier model that holds each custom modification along with the thing it's modifying? should custom modifiers be available directly to the character, or only via features, traits, etc.? Maybe instead of `custom modifiers` it's just `modifiers`.

    def __str__(self):
        return self.name

    def armor_class(self):
        # TODO: flesh this out -- additional modifiers
        return 10 + self.dexterity_modifier

    def proficiency_bonus(self):
        # from total level
        pass

    def hit_dice(self):
        # from class. anything else? just use class for default and allow modification (in which case will need a property like `hit_dice_if_different_from_class`)?
        pass

    def num_hit_die(self):
        # from total level. anything else?
        pass

    def initiative(self):
        # dex plus from feats plus custom modifiers
        pass

    def speed(self):
        # from race + modifiers
        pass

    def gain_experience(self, amount):
        self.experience_points += amount
        # self.save() ?


class Bond(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")


class PersonalityTrait(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")


class Ideal(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")


class Flaw(models.Model):
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, null=True, blank=True
    )
    name = models.CharField(max_length=500, default="")
    text = models.TextField(default="")


class ClassAndLevel(models.Model):
    """Mapping table for tracking a character's class and level in that class."""

    class Meta:
        verbose_name_plural = "classes and levels"

    character_class = models.ForeignKey(to=CharacterClass, on_delete=models.PROTECT)
    level = models.PositiveIntegerField()
    character = models.ForeignKey(to=Character, on_delete=models.CASCADE)
    # TODO: I'll probably want to add class selections here
