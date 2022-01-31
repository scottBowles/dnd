from django.contrib import admin
from .models import Artifact, ArtifactItem


class ConventionalArtifactItemInline(admin.StackedInline):
    model = ArtifactItem
    extra = 0


class ArtifactAdmin(admin.ModelAdmin):
    inlines = [ConventionalArtifactItemInline]


admin.site.register(Artifact, ArtifactAdmin)
