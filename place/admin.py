from django.contrib import admin
from .models import Planet, Region, Town, District, Location


admin.site.register(Planet)
admin.site.register(Region)
admin.site.register(Town)
admin.site.register(District)
admin.site.register(Location)
