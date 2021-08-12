from django.db import models
from django.contrib.auth.models import User


class AbilityScoreArrayMixin(models.Model):
    strength = models.PositiveIntegerField(default=10)
    dexterity = models.PositiveIntegerField(default=10)
    constitution = models.PositiveIntegerField(default=10)
    intelligence = models.PositiveIntegerField(default=10)
    wisdom = models.PositiveIntegerField(default=10)
    charisma = models.PositiveIntegerField(default=10)

    @property
    def strength_modifier(self):
        return self.strength // 2 - 5

    @property
    def dexterity_modifier(self):
        return self.dexterity // 2 - 5

    @property
    def constitution_modifier(self):
        return self.constitution // 2 - 5

    @property
    def intelligence_modifier(self):
        return self.intelligence // 2 - 5

    @property
    def wisdom_modifier(self):
        return self.wisdom // 2 - 5

    @property
    def charisma_modifier(self):
        return self.charisma // 2 - 5

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


class Character(AbilityScoreArrayMixin, MoneyHolderMixin):
    # Should I have characteristics that get recalculated and adjusted on save, or on save from related models, or on creation and on demand only? Worried about calculating too much on the fly.
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
    )  # many to many? include levels? default to some kind of commoner?
    level = models.PositiveIntegerField(default=1)  # sum character class?
    background = models.CharField(max_length=200, null=True, blank=True)  # fk
    race = models.CharField(max_length=200, null=True, blank=True)  # fk
    experience_points = models.PositiveIntegerField(default=0)
    hit_points = models.PositiveIntegerField(default=0)  # calculated?
    # hit_points_maximum
    # hit_points_current -- calculated? methods for taking damage, healing, effects from rests, etc.
    # hit_points_temporary
    # hit_points_damage_taken
    inspiration = models.BooleanField(default=False)
    # equipment = many to many. distinguish by type almost certainly. should have access to custom modifiers.
    # features and traits = many to many. should have access to custom modifiers. many will come from class, race, but will want own model to add custom.
    # attacks and spellcasting -- should come from spellcasting abilities, equipment. all should have unarmed.
    death_save_successes = models.PositiveIntegerField(default=0)  # reset as needed
    death_save_failures = models.PositiveIntegerField(default=0)  # reset as needed

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True
    )  # Create a Player model for this instead, accessing users through that? Seems like a one-to-one facade over user, unless users can have multiple players. Should we let users customize their player information per character (in which case one-to-many)?
    # Should the below be variants on one type of thing? `Character Flavor` or something?
    # personality_traits - many to many? one to many with each custom?
    # ideals - many to many? one to many with each custom?
    # bonds - many to many? one to many with each custom?
    # flaws - many to many? one to many with each custom?

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
