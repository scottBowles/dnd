from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from django.utils import timezone
import zoneinfo


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_activity_display", "last_login", "date_joined")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "email",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )
    list_display = (
        "username",
        "first_name",
        "last_name",
        "last_activity_display",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "last_activity",
    )
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    filter_horizontal = ()
    readonly_fields = ("last_login", "date_joined", "last_activity_display")

    @admin.display(description="Last activity")
    def last_activity_display(self, obj):
        # this was formerly the below before pytz was deprecated
        # return obj.last_activity.astimezone(pytz.timezone("US/Eastern")).strftime(
        #     "%B %d, %Y %-I:%M %p %Z"
        # )
        tz = zoneinfo.ZoneInfo("US/Eastern")
        formatted_date = obj.last_activity.astimezone(tz).strftime(
            "%B %d, %Y %-I:%M %p %Z"
        )
        return formatted_date
