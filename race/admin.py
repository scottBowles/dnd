from django.contrib import admin
from .models import Race


class RaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = ("created", "updated")


admin.site.register(Race, RaceAdmin)
