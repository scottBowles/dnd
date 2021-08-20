from django.contrib import admin

from character.models import (
    Bond,
    Flaw,
    Ideal,
    PersonalityTrait,
    ClassAndLevel,
    # Feature,
    InventoryArmor,
    InventoryWeapon,
    InventoryEquipment,
)


class PersonalityTraitInline(admin.TabularInline):
    model = PersonalityTrait
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


class BondInline(admin.TabularInline):
    model = Bond
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


class ClassAndLevelInline(admin.TabularInline):
    model = ClassAndLevel
    extra = 1
    classes = [
        "collapse",
    ]


# class FeaturesAndTraitsInline(admin.TabularInline):
#     model = Feature
#     extra = 1
#     classes = [
#         "collapse",
#     ]


class InventoryArmorInline(admin.TabularInline):
    model = InventoryArmor
    extra = 1


class InventoryWeaponInline(admin.TabularInline):
    model = InventoryWeapon
    extra = 1


class InventoryEquipmentInline(admin.TabularInline):
    model = InventoryEquipment
    extra = 1
