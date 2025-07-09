from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import AudioTranscript, TranscriptChunk


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
    list_filter = ("character_name", "was_split", "created", "session_audio__gamelog")
    search_fields = (
        "character_name",
        "original_filename",
        "transcript_text",
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
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Campaign Context",
            {
                "fields": ("campaign_context_display",),
                "classes": ("collapse",),
            },
        ),
        ("Raw Data", {"fields": ("whisper_response",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created", "updated"), "classes": ("collapse",)}),
    )

    inlines = [TranscriptChunkInline]

    @admin.display(description="Session Audio")
    def session_link(self, obj):
        return str(obj.session_audio)

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
        if not obj.campaign_context:
            return "No campaign context available"

        context_data = obj.campaign_context
        sections = []

        # Count totals
        total_entities = sum(
            len(v) for v in context_data.values() if isinstance(v, list)
        )
        summary = f"📊 {total_entities} entities"

        sections.append(f"<p><strong>{summary}</strong></p>")

        # Process each entity type
        for section_name, icon in [
            ("characters", "🎭"),
            ("places", "🏰"),
            ("items", "⚔️"),
            ("races", "🧝"),
            ("associations", "🏛️"),
        ]:
            entities = context_data.get(section_name, [])
            if not entities:
                continue

            # Sort: recent first, then alphabetically
            sorted_entities = sorted(
                entities,
                key=lambda x: (
                    not (
                        x.get("recently_mentioned", False)
                        if isinstance(x, dict)
                        else False
                    ),
                    x.get("name", str(x)) if isinstance(x, dict) else str(x),
                ),
            )

            sections.append(
                f"<p><strong>{icon} {section_name.title()} ({len(entities)})</strong></p>"
            )
            sections.append("<ul>")

            for entity in sorted_entities:
                if isinstance(entity, str):
                    sections.append(f"<li>{entity}</li>")
                elif isinstance(entity, dict):
                    name = entity.get("name", "Unknown")
                    description = entity.get("description", "")
                    recently_mentioned = entity.get("recently_mentioned", False)

                    # Get other property (race or type)
                    other_property = entity.get("race") or entity.get("type")

                    # Format: name (property) — description
                    entity_text = name
                    if other_property:
                        entity_text += f" ({other_property})"
                    if description:
                        entity_text += f" — {description}"
                    if recently_mentioned:
                        entity_text = f"🔥 {entity_text}"

                    sections.append(f"<li>{entity_text}</li>")
                else:
                    sections.append(f"<li>{str(entity)}</li>")

            sections.append("</ul>")

        return mark_safe("".join(sections))


@admin.register(TranscriptChunk)
class TranscriptChunkAdmin(admin.ModelAdmin):
    """Admin interface for transcript chunks."""

    list_display = (
        "id",
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
