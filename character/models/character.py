import math

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.aggregates import Sum
from graphql_relay import to_global_id
from .character_class import CharacterClass
from .mixins import HitDieMixin
from item.models import Equipment, Weapon, Armor
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
from nucleus.models import Entity
from association.models import Association


class CharacterQuerySet(models.QuerySet):
    def personality_traits(self):
        return self.personalitytrait_set.all()

    def ideals(self):
        return self.ideal_set.all()

    def bonds(self):
        return self.bond_set.all()

    def flaws(self):
        return self.flaw_set.all()


class Character(Entity):
    objects = CharacterQuerySet.as_manager()

    # NAME BLOCK
    name = models.CharField(max_length=200)
    race = models.ForeignKey(
        Race,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="characters",
    )
    description = models.TextField(null=True, blank=True)

    # FEATURES AND TRAITS BLOCK
    features_and_traits = models.ManyToManyField(
        Feature, related_name="npcs", blank=True
    )
    proficiencies = models.ManyToManyField(Proficiency, related_name="npcs", blank=True)
    associations = models.ManyToManyField(
        Association, related_name="characters", blank=True
    )
    related_characters = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
    )
    related_items = models.ManyToManyField(
        "item.Item",
        blank=True,
        related_name="related_characters",
    )
    related_places = models.ManyToManyField(
        "place.Place",
        blank=True,
        related_name="related_characters",
    )
    related_races = models.ManyToManyField(
        "race.Race",
        blank=True,
        related_name="related_characters",
    )

    def is_proficient(self, name, proficiency_type=None):
        if proficiency_type:
            return self.proficiencies.filter(
                name=name, proficiency_type=proficiency_type
            ).exists()
        else:
            return self.proficiencies.filter(name=name).exists()

    @property
    @admin.display(description="Languages (select as proficiencies)")
    def languages_proficient(self):
        language_proficiencies = self.proficiencies.filter(
            proficiency_type=Proficiency.LANGUAGE
        )
        names = language_proficiencies.values_list("name", flat=True)
        return list(Language.objects.filter(name__in=names))

    # TODO: These will need to use items as they exist, which themselves may need to be
    # amended so artifacts or unique objects are handled appropriately. Also, the through
    # tables will need to be created and we will need to make sure they do not clash with
    # the Character many to many fields and through tables.

    # # EQUIPMENT BLOCK
    # equipment = models.ManyToManyField(
    #     Equipment,
    #     through="InventoryEquipment",
    #     blank=True,
    #     related_name="equipment_inventories",
    # )

    # tool = models.ManyToManyField(
    #     Tool, through="InventoryTool", blank=True, related_name="tool_inventories"
    # )

    # SPELLCASTING BLOCK
    # TODO

    # # WEAPONS BLOCK
    # weapons = models.ManyToManyField(
    #     Weapon, through="InventoryWeapon", blank=True, related_name="weapon_inventories"
    # )

    # # ARMOR BLOCK
    # armor = models.ManyToManyField(
    #     Armor, through="InventoryArmor", blank=True, related_name="armor_inventories"
    # )

    # ATTACKS BLOCK
    # TODO

    # OTHER
    size = models.CharField(max_length=10, choices=SIZES, null=True, blank=True)

    def global_id(self):
        return to_global_id("Character", self.id)

    def __str__(self):
        return self.name or ""
