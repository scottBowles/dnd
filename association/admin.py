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
