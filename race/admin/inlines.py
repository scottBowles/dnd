from django.contrib import admin

from race.models import Race


class RaceRelatedAssociationsInline(admin.TabularInline):
    model = Race.related_associations.through
    extra = 1
    classes = [
        "collapse",
    ]


class RaceRelatedArtifactsInline(admin.TabularInline):
    model = Race.related_artifacts.through
    extra = 1
    classes = [
        "collapse",
    ]


class RaceRelatedCharactersInline(admin.TabularInline):
    model = Race.related_characters.through
    extra = 1
    classes = [
        "collapse",
    ]


class RaceRelatedItemsInline(admin.TabularInline):
    model = Race.related_items.through
    extra = 1
    classes = [
        "collapse",
    ]


class RaceRelatedPlacesInline(admin.TabularInline):
    model = Race.related_places.through
    extra = 1
    classes = [
        "collapse",
    ]
