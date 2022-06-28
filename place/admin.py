from django.contrib import admin
from .models import Place, Star, Planet, Moon, Region, Town, District, Location


class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = ("created", "updated")


admin.site.register(Place, PlaceAdmin)
admin.site.register(Star)
admin.site.register(Planet)
admin.site.register(Moon)
admin.site.register(Region)
admin.site.register(Town)
admin.site.register(District)
admin.site.register(Location)
