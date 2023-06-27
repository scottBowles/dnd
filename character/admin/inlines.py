from django.contrib import admin
from association.models import Association

from character.models import (
    Attack,
    Bond,
    ClassAndLevel,
    Flaw,
    Ideal,
    InventoryArmor,
    InventoryEquipment,
    InventoryTool,
    InventoryWeapon,
    PersonalityTrait,
)
from item.models import Artifact


class AttackInline(admin.StackedInline):
    model = Attack
    extra = 1
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("weapon", "range"),
                    "attack_bonus",
                    "ability_options",
                    "ability_modifiers",
                    (
                        "damage",
                        "damage_type",
                    ),
                    "properties",
                    "proficiency_needed",
                )
            },
        ),
    )
    readonly_fields = ("ability_modifiers",)


class BondInline(admin.TabularInline):
    model = Bond
    extra = 1
    classes = [
        "collapse",
    ]


class ClassAndLevelInline(admin.TabularInline):
    model = ClassAndLevel
    extra = 1
    classes = [
        "collapse",
    ]


class FlawInline(admin.TabularInline):
    model = Flaw
    extra = 1
    classes = [
        "collapse",
    ]


class IdealInline(admin.TabularInline):
    model = Ideal
    extra = 1
    classes = [
        "collapse",
    ]


class InventoryArmorInline(admin.TabularInline):
    model = InventoryArmor
    extra = 1


class InventoryEquipmentInline(admin.TabularInline):
    model = InventoryEquipment
    extra = 1


class InventoryToolInline(admin.TabularInline):
    model = InventoryTool
    extra = 1


class InventoryWeaponInline(admin.TabularInline):
    model = InventoryWeapon
    extra = 1


class PersonalityTraitInline(admin.TabularInline):
    model = PersonalityTrait
    extra = 1
    classes = [
        "collapse",
    ]


class CharacterRelatedArtifactsInline(admin.TabularInline):
    model = Artifact.related_characters.through
    extra = 1
    classes = [
        "collapse",
    ]


class CharacterRelatedAssociationsInline(admin.TabularInline):
    model = Association.related_characters.through
    extra = 1
    classes = [
        "collapse",
    ]
