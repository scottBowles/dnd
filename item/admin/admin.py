from django.contrib import admin
from ..models import (
    Item,
    Artifact,
    Equipment,
    Armor,
    Weapon,
)
from .inlines import (
    ArtifactTraitsInline,
    ArmorTraitsInline,
    WeaponTraitsInline,
    EquipmentTraitsInline,
)


class ItemAdmin(admin.ModelAdmin):
    inlines = [
        ArtifactTraitsInline,
        ArmorTraitsInline,
        WeaponTraitsInline,
        EquipmentTraitsInline,
    ]


class ArtifactAdmin(admin.ModelAdmin):
    inlines = [
        ArtifactTraitsInline,
    ]


class ArmorAdmin(admin.ModelAdmin):
    inlines = [
        ArmorTraitsInline,
    ]


class WeaponAdmin(admin.ModelAdmin):
    inlines = [
        WeaponTraitsInline,
    ]


class EquipmentAdmin(admin.ModelAdmin):
    inlines = [
        EquipmentTraitsInline,
    ]


admin.site.register(Item, ItemAdmin)
admin.site.register(Artifact, ArtifactAdmin)
admin.site.register(Armor, ArmorAdmin)
admin.site.register(Weapon, WeaponAdmin)
admin.site.register(Equipment, EquipmentAdmin)
