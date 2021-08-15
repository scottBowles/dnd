from django.contrib import admin

from character.models import Character, CharacterClass
from .inlines import (
    BondInline,
    FlawInline,
    IdealInline,
    PersonalityTraitInline,
    ClassAndLevelInline,
)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    # fieldsets = (
    #     (
    #         "Ability Scores",
    #         {
    #             "fields": (
    #                 (
    #                     "strength",
    #                     "dexterity",
    #                     "constitution",
    #                     "intelligence",
    #                     "wisdom",
    #                     "charisma",
    #                 ),
    #             )
    #         },
    #     ),
    #     (
    #         "Currency",
    #         {
    #             "fields": (
    #                 "total_cash_display",
    #                 (
    #                     "platinum_pieces",
    #                     "gold_pieces",
    #                     "electrum_pieces",
    #                     "silver_pieces",
    #                     "copper_pieces",
    #                 ),
    #             ),
    #         },
    #     ),
    # )

    # readonly_fields = ("total_cash_display",)

    readonly_fields = ("total_level",)

    inlines = [
        PersonalityTraitInline,
        IdealInline,
        BondInline,
        FlawInline,
        ClassAndLevelInline,
    ]

    # @admin.display(description="Total Cash on Hand (cp)")
    # def total_cash_display(self, obj):
    #     return obj.total_cash_on_hand


admin.site.register(CharacterClass)
