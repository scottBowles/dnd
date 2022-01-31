from django.contrib import admin
from ..models import ArtifactTraits, ArmorTraits, EquipmentTraits, WeaponTraits


class ArtifactTraitsInline(admin.TabularInline):
    model = ArtifactTraits
    extra = 1
    classes = [
        "collapse",
    ]


class ArmorTraitsInline(admin.TabularInline):
    model = ArmorTraits
    extra = 1
    classes = [
        "collapse",
    ]


class WeaponTraitsInline(admin.TabularInline):
    model = WeaponTraits
    extra = 1
    classes = [
        "collapse",
    ]


class EquipmentTraitsInline(admin.TabularInline):
    model = EquipmentTraits
    extra = 1
    classes = [
        "collapse",
    ]
