from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, GameLog, AiLogSuggestion
from django.utils import timezone
import zoneinfo
from django.utils.safestring import mark_safe


@admin.register(GameLog)
class GameLogAdmin(admin.ModelAdmin):
    fields = (
        "url",
        "copy_text_for_summary",
        "copy_text_for_ai_suggestions",
        "copy_text_for_ai_titles",
        "title",
        "google_id",
        "google_created_time",
        "game_date",
        "brief",
        "synopsis",
        "summary",
        "places_set_in",
    )
    readonly_fields = (
        "url",
        "copy_text_for_summary",
        "copy_text_for_ai_suggestions",
        "copy_text_for_ai_titles",
        "google_id",
        "google_created_time",
    )
    list_display = ("title", "google_created_time", "game_date")

    def copy_text_for_summary(self, obj):
        btn_id = "copy-text-helper"
        link_text = "Copy text for ai summary to clipboard"
        return mark_safe(
            f"""
            <textarea id="{btn_id}" style="position: absolute; top: -10000px">{obj.copy_text_for_summary()}</textarea>
            <a href="#" onclick="document.querySelector(\'#{btn_id}\').select(); document.execCommand(\'copy\');" class="addlink">{link_text}</a>
            """
        )

    copy_text_for_summary.short_description = "Copy text for summary"

    def copy_text_for_ai_suggestions(self, obj):
        btn_id = "copy-suggestions-helper"
        link_text = "Copy text for ai suggestions to clipboard"
        return mark_safe(
            f"""
            <textarea id="{btn_id}" style="position: absolute; top: -10000px">{obj.copy_text_for_ai_suggestions()}</textarea>
            <a href="#" onclick="document.querySelector(\'#{btn_id}\').select(); document.execCommand(\'copy\');" class="addlink">{link_text}</a>
            """
        )

    copy_text_for_ai_suggestions.short_description = "Copy text for ai suggestions"

    def copy_text_for_ai_titles(self, obj):
        btn_id = "copy-titles-helper"
        link_text = "Copy text for ai titles to clipboard"
        return mark_safe(
            f"""
            <textarea id="{btn_id}" style="position: absolute; top: -10000px">{obj.copy_text_for_ai_titles()}</textarea>
            <a href="#" onclick="document.querySelector(\'#{btn_id}\').select(); document.execCommand(\'copy\');" class="addlink">{link_text}</a>
            """
        )

    copy_text_for_ai_suggestions.short_description = "Copy text for ai titles"


@admin.register(AiLogSuggestion)
class AiLogSuggestionAdmin(admin.ModelAdmin):
    pass


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
