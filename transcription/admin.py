from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import TranscriptionSession, AudioTranscript, TranscriptChunk


class TranscriptChunkInline(admin.TabularInline):
    """Inline editor for transcript chunks."""

    model = TranscriptChunk
    extra = 0
    readonly_fields = (
        "chunk_number",
        "filename",
        "start_time_offset",
        "duration_seconds",
    )
    fields = (
        "chunk_number",
        "filename",
        "start_time_offset",
        "duration_seconds",
        "chunk_text",
    )

    def has_add_permission(self, request, obj=None):
        return False  # Chunks are created programmatically


class AudioTranscriptInline(admin.TabularInline):
    """Inline editor for audio transcripts."""

    model = AudioTranscript
    extra = 0
    readonly_fields = (
        "original_filename",
        "character_name",
        "file_size_mb",
        "chunks_link",
    )
    fields = (
        "original_filename",
        "character_name",
        "file_size_mb",
        "was_split",
        "num_chunks",
        "chunks_link",
    )

    @admin.display(description="Chunks")
    def chunks_link(self, obj):
        if obj.pk:
            url = reverse("admin:transcription_audiotranscript_change", args=[obj.pk])
            return format_html('<a href="{}">View {} chunks</a>', url, obj.num_chunks)
        return "Save to view chunks"

    def has_add_permission(self, request, obj=None):
        return False  # Transcripts are created programmatically


@admin.register(TranscriptionSession)
class TranscriptionSessionAdmin(admin.ModelAdmin):
    """Admin interface for transcription sessions."""

    list_display = (
        "id",
        "log_title",
        "transcript_count",
        "total_duration",
        "created",
        "updated",
    )
    list_filter = ("created", "updated")
    search_fields = ("notes", "log__title", "log__url")
    readonly_fields = ("created", "updated", "transcript_count", "total_duration")

    fieldsets = (
        (None, {"fields": ("log", "notes")}),
        (
            "Metadata",
            {
                "fields": ("created", "updated", "transcript_count", "total_duration"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [AudioTranscriptInline]

    @admin.display(description="GameLog", ordering="log__title")
    def log_title(self, obj):
        if obj.log:
            return obj.log.title or obj.log.url
        return "No GameLog"

    @admin.display(description="Transcripts")
    def transcript_count(self, obj):
        return obj.transcripts.count()

    @admin.display(description="Total Duration")
    def total_duration(self, obj):
        total = sum(t.duration_minutes or 0 for t in obj.transcripts.all())
        if total > 0:
            hours = int(total // 60)
            minutes = int(total % 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "Unknown"


@admin.register(AudioTranscript)
class AudioTranscriptAdmin(admin.ModelAdmin):
    """Admin interface for audio transcripts."""

    list_display = (
        "character_name",
        "original_filename",
        "session_link",
        "file_size_mb",
        "duration_display",
        "num_chunks",
        "was_split",
        "created",
    )
    list_filter = ("character_name", "was_split", "created", "session__log")
    search_fields = (
        "character_name",
        "original_filename",
        "transcript_text",
        "session__notes",
    )
    readonly_fields = (
        "created",
        "updated",
        "file_size_mb",
        "duration_minutes",
        "was_split",
        "num_chunks",
        "processing_time_seconds",
        "preview_text",
        "campaign_context_display",
    )

    fieldsets = (
        (
            "File Information",
            {
                "fields": (
                    "session",
                    "original_filename",
                    "character_name",
                    "file_size_mb",
                    "duration_minutes",
                )
            },
        ),
        ("Transcription", {"fields": ("preview_text", "transcript_text")}),
        (
            "Processing Details",
            {
                "fields": (
                    "was_split",
                    "num_chunks",
                    "processing_time_seconds",
                    "campaign_context_display",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Raw Data", {"fields": ("whisper_response",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created", "updated"), "classes": ("collapse",)}),
    )

    inlines = [TranscriptChunkInline]

    @admin.display(description="Session")
    def session_link(self, obj):
        url = reverse(
            "admin:transcription_transcriptionsession_change", args=[obj.session.pk]
        )
        return format_html('<a href="{}">{}</a>', url, str(obj.session))

    @admin.display(description="Duration", ordering="duration_minutes")
    def duration_display(self, obj):
        if obj.duration_minutes:
            minutes = int(obj.duration_minutes)
            seconds = int((obj.duration_minutes % 1) * 60)
            return f"{minutes}:{seconds:02d}"
        return "Unknown"

    @admin.display(description="Transcript Preview")
    def preview_text(self, obj):
        if obj.transcript_text:
            preview = obj.transcript_text[:200]
            if len(obj.transcript_text) > 200:
                preview += "..."
            return preview
        return "No transcript"

    @admin.display(description="Campaign Context")
    def campaign_context_display(self, obj):
        if obj.campaign_context:
            context_items = []
            for key, value in obj.campaign_context.items():
                if isinstance(value, list) and value:
                    context_items.append(f"{key}: {len(value)} items")
                elif value:
                    context_items.append(f"{key}: {value}")
            return (
                mark_safe("<br>".join(context_items)) if context_items else "No context"
            )
        return "No context"


@admin.register(TranscriptChunk)
class TranscriptChunkAdmin(admin.ModelAdmin):
    """Admin interface for transcript chunks."""

    list_display = (
        "transcript_link",
        "chunk_number",
        "filename",
        "start_time_display",
        "duration_display",
        "preview_text",
        "created",
    )
    list_filter = ("transcript__character_name", "created")
    search_fields = (
        "filename",
        "chunk_text",
        "transcript__character_name",
        "transcript__original_filename",
    )
    readonly_fields = (
        "created",
        "updated",
        "start_time_offset",
        "duration_seconds",
        "filename",
        "preview_text",
    )

    fieldsets = (
        (
            "Chunk Information",
            {
                "fields": (
                    "transcript",
                    "chunk_number",
                    "filename",
                    "start_time_offset",
                    "duration_seconds",
                )
            },
        ),
        ("Transcription", {"fields": ("preview_text", "chunk_text")}),
        ("Raw Data", {"fields": ("whisper_response",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created", "updated"), "classes": ("collapse",)}),
    )

    @admin.display(description="Audio Transcript")
    def transcript_link(self, obj):
        url = reverse(
            "admin:transcription_audiotranscript_change", args=[obj.transcript.pk]
        )
        return format_html('<a href="{}">{}</a>', url, str(obj.transcript))

    @admin.display(description="Start Time", ordering="start_time_offset")
    def start_time_display(self, obj):
        minutes = int(obj.start_time_offset // 60)
        seconds = int(obj.start_time_offset % 60)
        return f"{minutes}:{seconds:02d}"

    @admin.display(description="Duration", ordering="duration_seconds")
    def duration_display(self, obj):
        minutes = int(obj.duration_seconds // 60)
        seconds = int(obj.duration_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    @admin.display(description="Text Preview")
    def preview_text(self, obj):
        if obj.chunk_text:
            preview = obj.chunk_text[:150]
            if len(obj.chunk_text) > 150:
                preview += "..."
            return preview
        return "No transcript"
