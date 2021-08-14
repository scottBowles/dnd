from django.contrib import admin

from character.models import Character
from .inlines import BondInline, FlawInline, IdealInline, PersonalityTraitInline


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    inlines = [
        PersonalityTraitInline,
        IdealInline,
        BondInline,
        FlawInline,
    ]
