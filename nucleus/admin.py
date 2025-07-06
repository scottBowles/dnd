from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, GameLog, AiLogSuggestion, SessionAudio
from django.utils import timezone
import zoneinfo
from django.utils.safestring import mark_safe
from transcription.services import transcribe_session_audio
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from transcription.services import TranscriptionService


class SessionAudioInline(admin.TabularInline):
    model = SessionAudio
    extra = 1
    fields = (
        "file",
        "original_filename",
        "uploaded_by",
        "transcription_status",
        "file_size_mb",
        "created",
        "updated",
    )
    readonly_fields = ("file_size_mb", "created", "updated")


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
        "audio_session_notes",
        "last_game_log",
    )
    readonly_fields = (
        "copy_text_for_summary",
        "copy_text_for_ai_suggestions",
        "copy_text_for_ai_titles",
        "google_id",
        "google_created_time",
    )
    list_display = ("title", "google_created_time", "game_date")
    inlines = [SessionAudioInline]
    actions = ["transcribe_audio_files_action"]
    change_form_template = "admin/nucleus/gamelog/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/transcribe-audio-files/",
                self.admin_site.admin_view(self.transcribe_audio_files_detail_view),
                name="nucleus_gamelog_transcribe_audio_files_detail",
            ),
            path(
                "<int:object_id>/generate-session-log-concat/",
                self.admin_site.admin_view(self.generate_session_log_concat_view),
                name="nucleus_gamelog_generate_session_log_concat",
            ),
            path(
                "<int:object_id>/generate-session-log-segment/",
                self.admin_site.admin_view(self.generate_session_log_segment_view),
                name="nucleus_gamelog_generate_session_log_segment",
            ),
        ]
        return custom_urls + urls

    def _can_generate_log(self, gamelog, request):
        # Check for existing generated_log_text
        if gamelog.generated_log_text and gamelog.generated_log_text.strip():
            messages.warning(request, "Generated log already exists. Not overwriting.")
            return False
        # Check for related AudioTranscripts
        from transcription.models import AudioTranscript

        if not AudioTranscript.objects.filter(session_audio__gamelog=gamelog).exists():
            messages.warning(request, "No related AudioTranscripts to transcribe.")
            return False
        return True

    def generate_session_log_concat_view(self, request, object_id):
        gamelog = self.get_object(request, object_id)
        if not gamelog:
            messages.error(request, "GameLog not found.")
            return redirect("..")
        if not self._can_generate_log(gamelog, request):
            return redirect(request.path.replace("generate-session-log-concat/", ""))
        try:
            service = TranscriptionService()
            result = service.generate_session_log_async(
                gamelog, method="concat", use_celery=settings.CELERY_BROKER_URL
            )
            if hasattr(result, "id"):  # Celery AsyncResult
                messages.success(
                    request,
                    f"Session log (concat) generation started. Task ID: {result.id}",
                )
            else:
                messages.success(request, "Session log (concat) generated and saved.")
        except Exception as e:
            messages.error(request, f"Error generating session log: {e}")
        return redirect(request.path.replace("generate-session-log-concat/", ""))

    def generate_session_log_segment_view(self, request, object_id):
        gamelog = self.get_object(request, object_id)
        if not gamelog:
            messages.error(request, "GameLog not found.")
            return redirect("..")
        if not self._can_generate_log(gamelog, request):
            return redirect(request.path.replace("generate-session-log-segment/", ""))
        try:
            service = TranscriptionService()
            result = service.generate_session_log_async(
                gamelog, method="segment", use_celery=settings.CELERY_BROKER_URL
            )
            if hasattr(result, "id"):  # Celery AsyncResult
                messages.success(
                    request,
                    f"Session log (segment) generation started. Task ID: {result.id}",
                )
            else:
                messages.success(request, "Session log (segment) generated and saved.")
        except Exception as e:
            messages.error(request, f"Error generating session log: {e}")
        return redirect(request.path.replace("generate-session-log-segment/", ""))

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

    def _transcribe_audio_files_for_gamelogs(self, request, gamelogs):
        print("_transcribe_audio_files_for_gamelogs called with gamelogs:", gamelogs)
        """
        Shared logic for transcribing audio files for one or more GameLogs.
        """
        from transcription.services import transcribe_session_audio
        from django.contrib import messages

        for gamelog in gamelogs:
            session_notes = gamelog.audio_session_notes or ""
            previous_transcript = ""
            if gamelog.last_game_log:
                previous_transcript = (
                    getattr(gamelog.last_game_log, "log_text", "") or ""
                )
            audio_files = gamelog.session_audio_files.all()
            print(".   audio_files:", audio_files)
            if not audio_files:
                messages.warning(request, f"No audio files found for {gamelog}.")
                continue

            async_tasks = []
            for audio in audio_files:
                if (
                    hasattr(audio, "audio_transcripts")
                    and audio.audio_transcripts.exists()
                ):
                    messages.info(
                        request, f"Skipping {audio}: transcript already exists."
                    )
                    continue
                audio.transcription_status = "processing"
                audio.save(update_fields=["transcription_status"])
                try:
                    result = transcribe_session_audio(
                        audio,
                        session_notes=session_notes,
                        previous_transcript=previous_transcript,
                        use_celery=bool(settings.CELERY_BROKER_URL),
                    )
                    # Check if result is a Celery AsyncResult (async processing)
                    if hasattr(result, "id"):  # Celery AsyncResult
                        async_tasks.append((audio, result.id))
                        # Don't immediately mark as completed since it's async
                    elif result:  # Synchronous processing success
                        audio.transcription_status = "completed"
                        audio.save(update_fields=["transcription_status"])
                    else:  # Synchronous processing failure
                        audio.transcription_status = "failed"
                        audio.save(update_fields=["transcription_status"])
                except Exception as e:
                    audio.transcription_status = "failed"
                    audio.save(update_fields=["transcription_status"])
                    messages.error(request, f"Failed to transcribe {audio}: {e}")

            if async_tasks:
                task_info = ", ".join(
                    [
                        f"{audio.original_filename} (Task: {task_id})"
                        for audio, task_id in async_tasks
                    ]
                )
                messages.success(
                    request,
                    f"Transcription started for {len(async_tasks)} audio files in {gamelog}. "
                    f"Tasks: {task_info}. Check Celery worker logs for progress.",
                )
            else:
                messages.success(
                    request,
                    f"Transcription attempted for all audio files in {gamelog}.",
                )

    def transcribe_audio_files_action(self, request, queryset):
        """
        Admin action to transcribe all SessionAudio files for selected GameLogs.
        """
        self._transcribe_audio_files_for_gamelogs(request, queryset)

    def transcribe_audio_files_detail_view(self, request, object_id):
        print("transcribe_audio_files_detail_view called with object_id:", object_id)
        gamelog = self.get_object(request, object_id)
        if not gamelog:
            messages.error(request, "GameLog not found.")
            return redirect("..")
        self._transcribe_audio_files_for_gamelogs(request, [gamelog])
        return redirect(request.path.replace("transcribe-audio-files/", ""))


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


@admin.register(SessionAudio)
class SessionAudioAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "gamelog",
        "transcription_status",
        "file_size_mb",
        "uploaded_by",
        "created",
    )
    list_filter = ("transcription_status", "created")
    search_fields = ("original_filename", "gamelog__title")
    readonly_fields = ("file_size_mb", "created", "updated")
    fields = (
        "file",
        "gamelog",
        "original_filename",
        "uploaded_by",
        "transcription_status",
        "file_size_mb",
        "created",
        "updated",
    )
    actions = ["transcribe_selected_audio"]

    def save_model(self, request, obj, form, change):
        if not change:  # Only set on creation
            if not obj.uploaded_by:
                obj.uploaded_by = request.user
            if not obj.original_filename and obj.file:
                obj.original_filename = obj.file.name
        super().save_model(request, obj, form, change)

    def transcribe_selected_audio(self, request, queryset):
        """
        Admin action to transcribe selected SessionAudio files.
        """
        count = 0
        async_count = 0
        for audio in queryset:
            audio.transcription_status = "processing"
            audio.save(update_fields=["transcription_status"])
            try:
                result = transcribe_session_audio(audio)
                # Check if result is a Celery AsyncResult (async processing)
                if hasattr(result, "id"):  # Celery AsyncResult
                    async_count += 1
                    # Don't immediately mark as completed since it's async
                elif result:  # Synchronous processing success
                    audio.transcription_status = "completed"
                    audio.save(update_fields=["transcription_status"])
                else:  # Synchronous processing failure
                    audio.transcription_status = "failed"
                    audio.save(update_fields=["transcription_status"])
            except Exception as e:
                audio.transcription_status = "failed"
                audio.save(update_fields=["transcription_status"])
            count += 1

        if async_count > 0:
            self.message_user(
                request,
                f"Transcription started for {count} audio file(s). "
                f"{async_count} are being processed asynchronously - check worker logs for progress.",
            )
        else:
            self.message_user(
                request, f"Transcription triggered for {count} audio file(s)."
            )

    transcribe_selected_audio.short_description = "Transcribe selected audio files"
