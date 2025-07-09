"""
Models for storing transcription data and metadata.
"""

from django.db import models
from django.db.models import JSONField
from nucleus.models import BaseModel


class AudioTranscript(BaseModel):
    """Stores transcript data for individual audio files."""

    session_audio = models.ForeignKey(
        "nucleus.SessionAudio",
        on_delete=models.CASCADE,
        related_name="audio_transcripts",
    )

    # File information
    original_filename = models.CharField(max_length=255)
    character_name = models.CharField(max_length=100)
    file_size_mb = models.FloatField()
    duration_minutes = models.FloatField(null=True, blank=True)

    # Transcription data
    transcript_text = models.TextField()
    whisper_response = JSONField(default=dict)  # Full Whisper API response

    # Processing metadata
    was_split = models.BooleanField(default=False)
    num_chunks = models.PositiveIntegerField(default=1)
    processing_time_seconds = models.FloatField(null=True, blank=True)

    # Campaign context used
    campaign_context = JSONField(default=dict)

    class Meta:
        ordering = ["character_name", "original_filename"]

    def __str__(self):
        return f"{self.character_name} - {self.original_filename}"


class TranscriptChunk(BaseModel):
    """Stores data for individual chunks of split audio files."""

    transcript = models.ForeignKey(
        AudioTranscript, on_delete=models.CASCADE, related_name="chunks"
    )

    chunk_number = models.PositiveIntegerField()
    filename = models.CharField(max_length=255)
    start_time_offset = models.FloatField()  # Seconds from start of original file
    duration_seconds = models.FloatField()

    # Chunk-specific transcription
    chunk_text = models.TextField()
    whisper_response = JSONField(default=dict)

    class Meta:
        ordering = ["transcript", "chunk_number"]

    def __str__(self):
        return f"{self.transcript.character_name} - Chunk {self.chunk_number}"
