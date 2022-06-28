from django.contrib import admin

from character.models import Character, CharacterClass, NPC
from .inlines import (
    ClassAndLevelInline,
    AttackInline,
    BondInline,
    FlawInline,
    IdealInline,
    PersonalityTraitInline,
    InventoryArmorInline,
    InventoryWeaponInline,
    InventoryEquipmentInline,
    InventoryToolInline,
)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Character",
            {
                "fields": (
                    ("name", "player_name"),
                    ("class_level_display", "total_level"),
                    (
                        "race",
                        "background",
                        "alignment",
                        "experience_points",
                    ),
                )
            },
        ),
        (
            "Inspiration and Proficiency",
            {"fields": (("inspiration", "proficiency_bonus"),)},
        ),
        (
            "Ability Scores",
            {
                "fields": (
                    (
                        "strength",
                        "dexterity",
                        "constitution",
                        "intelligence",
                        "wisdom",
                        "charisma",
                    ),
                )
            },
        ),
        (
            "Saving Throws",
            {
                "fields": (
                    (
                        "strength_save",
                        "dexterity_save",
                        "constitution_save",
                        "intelligence_save",
                        "wisdom_save",
                        "charisma_save",
                    ),
                ),
            },
        ),
        (
            "Vitals",
            {
                "fields": (
                    (
                        "armor_class",
                        "initiative",
                        "speed",
                    ),
                    (
                        "max_hit_points",
                        "temporary_hit_points",
                        "damage_taken",
                        "hit_points_current",
                    ),
                    (
                        "hit_die",
                        "num_hit_dice",
                    ),
                    ("death_save_successes", "death_save_failures"),
                )
            },
        ),
        (
            "Currency",
            {
                "fields": (
                    "total_cash_on_hand",
                    (
                        "platinum_pieces",
                        "gold_pieces",
                        "electrum_pieces",
                        "silver_pieces",
                        "copper_pieces",
                    ),
                ),
            },
        ),
        (
            "Proficiencies",
            {
                "fields": ("proficiencies", "languages_proficient"),
            },
        ),
        (
            "Features and Traits",
            {"fields": ("features_and_traits",)},
        ),
    )

    readonly_fields = (
        "total_cash_on_hand",
        "total_level",
        "class_level_display",
        "proficiency_bonus",
        "strength_save",
        "dexterity_save",
        "constitution_save",
        "intelligence_save",
        "wisdom_save",
        "charisma_save",
        "hit_points_current",
        "languages_proficient",
    )

    inlines = [
        InventoryArmorInline,
        InventoryWeaponInline,
        InventoryEquipmentInline,
        InventoryToolInline,
        PersonalityTraitInline,
        IdealInline,
        BondInline,
        FlawInline,
        ClassAndLevelInline,
        AttackInline,
    ]

    @admin.display(description="Total Cash on Hand (cp)")
    def total_cash_display(self, obj):
        return obj.total_cash_on_hand

    @admin.display(description="Classes and Levels (input in inline below)")
    def class_level_display(self, obj):
        return ", ".join(
            [
                "{} ({})".format(cl.class_name, cl.level)
                for cl in obj.classandlevel_set.all().order_by("character_class")
            ]
        )

    @admin.display(description="Total Level")
    def total_level(self, obj):
        return obj.total_level()


class NPCAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "lock_user",
        "lock_time",
        "updated",
        "created",
    )
    list_filter = ("created", "updated")


admin.site.register(CharacterClass)
admin.site.register(NPC, NPCAdmin)
