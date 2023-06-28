from django.contrib import admin
from .models import Association


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
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
        "related_associations",
        "related_artifacts",
        "related_characters",
        "related_items",
        "related_places",
        "related_races",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
