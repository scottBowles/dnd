from django.contrib import admin
from ..models import Item, Artifact
from .inlines import ArmorTraitsInline, WeaponTraitsInline, EquipmentTraitsInline


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_armor",
        "is_weapon",
        "is_equipment",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = (
        "created",
        "updated",
    )

    @admin.display(boolean=True, description="Armor")
    def is_armor(self, obj):
        return obj.armor is not None

    @admin.display(boolean=True, description="Weapon")
    def is_weapon(self, obj):
        return obj.weapon is not None

    @admin.display(boolean=True, description="Equipment")
    def is_equipment(self, obj):
        return obj.equipment is not None

    inlines = [
        ArmorTraitsInline,
        WeaponTraitsInline,
        EquipmentTraitsInline,
    ]


class ArtifactAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = ("created", "updated")


admin.site.register(Item, ItemAdmin)
admin.site.register(Artifact, ArtifactAdmin)
