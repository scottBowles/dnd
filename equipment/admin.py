from django.contrib import admin
from .models import Equipment, Armor, Weapon

# Register your models here.
admin.site.register(Equipment)
admin.site.register(Armor)
admin.site.register(Weapon)
