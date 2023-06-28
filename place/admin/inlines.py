from django.contrib import admin

from place.models.place import Place


class PlaceRelatedAssociationsInline(admin.TabularInline):
    model = Place.related_associations.through
    extra = 1
    classes = [
        "collapse",
    ]


class PlaceRelatedArtifactsInline(admin.TabularInline):
    model = Place.related_artifacts.through
    extra = 1
    classes = [
        "collapse",
    ]


class PlaceRelatedCharactersInline(admin.TabularInline):
    model = Place.related_characters.through
    extra = 1
    classes = [
        "collapse",
    ]


class PlaceRelatedItemsInline(admin.TabularInline):
    model = Place.related_items.through
    extra = 1
    classes = [
        "collapse",
    ]
