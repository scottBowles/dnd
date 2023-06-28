from django.contrib import admin
from ..models import Race
from .inlines import (
    RaceRelatedItemsInline,
    RaceRelatedAssociationsInline,
    RaceRelatedArtifactsInline,
    RaceRelatedCharactersInline,
    RaceRelatedPlacesInline,
)


class RaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = ("created", "updated")
    readonly_fields = (
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    fields = (
        "name",
        "description",
        "lock_user",
        "lock_time",
        "updated",
        "created",
        "related_races",
    )
    inlines = [
        RaceRelatedItemsInline,
        RaceRelatedAssociationsInline,
        RaceRelatedArtifactsInline,
        RaceRelatedCharactersInline,
        RaceRelatedPlacesInline,
    ]


admin.site.register(Race, RaceAdmin)
