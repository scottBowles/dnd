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
    inlines = [
        PersonalityTraitInline,
        IdealInline,
        BondInline,
        FlawInline,
        ClassAndLevelInline,
    ]


admin.site.register(CharacterClass)
