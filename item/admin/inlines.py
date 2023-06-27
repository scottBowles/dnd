from django.contrib import admin

from ..models import ArmorTraits, Artifact, EquipmentTraits, Item, WeaponTraits


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


class ArtifactRelatedAssociationsInline(admin.TabularInline):
    model = Artifact.related_associations.through
    extra = 1
    classes = [
        "collapse",
    ]


class ItemRelatedAssociationsInline(admin.TabularInline):
    model = Item.related_associations.through
    extra = 1
    classes = [
        "collapse",
    ]


class ItemRelatedArtifactsInline(admin.TabularInline):
    model = Item.related_artifacts.through
    extra = 1
    classes = [
        "collapse",
    ]


class ItemRelatedCharactersInline(admin.TabularInline):
    model = Item.related_characters.through
    extra = 1
    classes = [
        "collapse",
    ]
