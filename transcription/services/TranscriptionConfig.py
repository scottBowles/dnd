import os
from typing import Optional

from django.conf import settings


class TranscriptionConfig:
    """Configuration settings for transcription service."""

    def __init__(
        self,
        max_file_size_mb: int = 10,
        chunk_duration_minutes: int = 10,
        delay_between_requests: int = 21,
        recent_threshold_days: int = 180,
        openai_api_key: Optional[str] = None,
        enable_text_cleaning: bool = True,
        enable_audio_preprocessing: bool = True,
        repetition_detection_threshold: float = 0.4,
        max_allowed_repetitions: int = 3,
    ):
        """Initialize configuration settings."""

        # API Configuration
        self.openai_api_key = openai_api_key or getattr(
            settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")
        )

        # File Processing
        self.max_file_size_mb = max_file_size_mb  # Buffer under 25MB Whisper limit
        self.chunk_duration_minutes = chunk_duration_minutes
        self.audio_extensions = [".flac", ".wav", ".aac", ".m4a", ".mp3"]

        # API Settings
        self.delay_between_requests = delay_between_requests  # seconds
        self.recent_threshold_days = recent_threshold_days  # 6 months

        # Text Processing Settings
        self.enable_text_cleaning = enable_text_cleaning
        self.repetition_detection_threshold = repetition_detection_threshold
        self.max_allowed_repetitions = max_allowed_repetitions

        # Audio Processing Settings
        self.enable_audio_preprocessing = enable_audio_preprocessing
