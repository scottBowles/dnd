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


class ItemMixin(admin.ModelAdmin):
    fields = [
        "name",
        "description",
    ]

    list_display = [
        "name",
        "is_artifact",
        "is_armor",
        "is_weapon",
        "is_equipment",
    ]

    @admin.display(boolean=True, description="Artifact")
    def is_artifact(self, obj):
        return obj.artifact is not None

    @admin.display(boolean=True, description="Armor")
    def is_armor(self, obj):
        return obj.armor is not None

    @admin.display(boolean=True, description="Weapon")
    def is_weapon(self, obj):
        return obj.weapon is not None

    @admin.display(boolean=True, description="Equipment")
    def is_equipment(self, obj):
        return obj.equipment is not None

    class Meta:
        abstract = True


class ItemAdmin(ItemMixin):
    inlines = [
        ArtifactTraitsInline,
        ArmorTraitsInline,
        WeaponTraitsInline,
        EquipmentTraitsInline,
    ]


class ArtifactAdmin(ItemMixin):
    inlines = [
        ArtifactTraitsInline,
    ]


class ArmorAdmin(ItemMixin):
    inlines = [
        ArmorTraitsInline,
    ]


class WeaponAdmin(ItemMixin):
    inlines = [
        WeaponTraitsInline,
    ]


class EquipmentAdmin(ItemMixin):
    inlines = [
        EquipmentTraitsInline,
    ]


admin.site.register(Item, ItemAdmin)
admin.site.register(Artifact, ArtifactAdmin)
admin.site.register(Armor, ArmorAdmin)
admin.site.register(Weapon, WeaponAdmin)
admin.site.register(Equipment, EquipmentAdmin)
