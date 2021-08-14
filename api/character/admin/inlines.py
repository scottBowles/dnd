from django.contrib import admin

from character.models import Bond, Flaw, Ideal, PersonalityTrait


class PersonalityTraitInline(admin.TabularInline):
    model = PersonalityTrait
    classes = [
        "collapse",
    ]


class IdealInline(admin.TabularInline):
    model = Ideal
    classes = [
        "collapse",
    ]


class BondInline(admin.TabularInline):
    model = Bond
    classes = [
        "collapse",
    ]


class FlawInline(admin.TabularInline):
    model = Flaw
    classes = [
        "collapse",
    ]
