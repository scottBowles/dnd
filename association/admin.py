from django.contrib import admin
from .models import Association


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created", "updated")
    list_filter = ("created", "updated")
