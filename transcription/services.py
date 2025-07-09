"""
Transcription services for D&D audio files.
Provides Whisper API integration with campaign-specific context enhancement.
"""

import math
import os
import re
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openai
from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from pydub import AudioSegment

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import GameLog, SessionAudio
from place.models import Place
from race.models import Race

from .models import AudioTranscript, TranscriptChunk
from .responses import WhisperResponse
from .utils import ordinal


class TranscriptCleaner:
    """Utility for cleaning up repetitive patterns and noise in Whisper transcripts."""

    @staticmethod
    def clean_repetitive_text(text: str, max_repetitions: int = 3) -> str:
        """
        Remove repetitive patterns from transcript text.

        Args:
            text: The transcript text to clean
            max_repetitions: Maximum allowed repetitions before removal

        Returns:
            Cleaned text with repetitive patterns reduced
        """
        if not text or not text.strip():
            return text

        # Pattern 1: Exact word repetitions (e.g., "Okay. Okay. Okay.")
        # Match word followed by punctuation, repeated multiple times
        pattern1 = r"\b(\w+[.,!?]*)\s*(?:\1\s*){" + str(max_repetitions) + r",}"
        text = re.sub(
            pattern1,
            lambda m: (m.group(1) + " ") * max_repetitions,
            text,
            flags=re.IGNORECASE,
        )

        # Pattern 2: Phrase repetitions (e.g., "in the, in the, in the")
        # Match 2-4 word phrases repeated multiple times
        pattern2 = r"\b((?:\w+\s*[,.]?\s*){1,4}?)(?:\1){" + str(max_repetitions) + r",}"
        text = re.sub(
            pattern2,
            lambda m: m.group(1) * max_repetitions,
            text,
            flags=re.IGNORECASE,
        )

        # Pattern 3: Single letter repetitions (e.g., "a a a a a")
        pattern3 = r"\b(\w)\s*(?:\1\s*){" + str(max_repetitions) + r",}"
        text = re.sub(pattern3, lambda m: m.group(1) + " ", text, flags=re.IGNORECASE)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    @staticmethod
    def detect_low_quality_segments(text: str, threshold: float = 0.3) -> bool:
        """
        Detect if a text segment appears to be low quality based on repetition ratio.

        Args:
            text: Text to analyze
            threshold: Ratio of repetitive content that indicates low quality

        Returns:
            True if segment appears to be low quality
        """
        if not text or len(text.split()) < 10:
            return False

        words = text.lower().split()
        word_count = len(words)
        unique_words = len(set(words))

        # Calculate repetition ratio
        repetition_ratio = 1 - (unique_words / word_count)

        return repetition_ratio > threshold

    @staticmethod
    def remove_low_quality_segments(text: str, threshold: float = 0.3) -> str:
        """
        Remove segments that appear to be low quality based on repetition.

        Args:
            text: Full transcript text
            threshold: Repetition threshold for removal

        Returns:
            Text with low-quality segments removed
        """
        # Split on sentence boundaries
        sentences = re.split(r"[.!?]+", text)
        cleaned_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not TranscriptCleaner.detect_low_quality_segments(
                sentence, threshold
            ):
                cleaned_sentences.append(sentence)

        return ". ".join(cleaned_sentences) + "." if cleaned_sentences else ""


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
        repetition_detection_threshold: float = 0.6,  # Increased from 0.4 to reduce false positives
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


class CampaignContextService:
    """Service for fetching and formatting campaign context from database."""

    def __init__(self, config: TranscriptionConfig):
        """Initialize with configuration instance."""
        self.config = config

    def get_campaign_context(self, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relevant D&D campaign context from the database.
        Prioritizes entities that have been recently mentioned in game logs.
        """
        context = {
            "characters": [],
            "places": [],
            "races": [],
            "items": [],
            "associations": [],
        }

        try:
            # Calculate recent threshold
            recent_threshold = timezone.now() - timedelta(
                days=self.config.recent_threshold_days
            )

            def get_entities_by_recency(model, entity_limit):
                """Helper to get entities ordered by recent log mentions."""
                return model.objects.annotate(
                    most_recent_log_date=Max("logs__game_date")
                ).order_by("-most_recent_log_date", "name")[:entity_limit]

            # Get Characters (NPCs)
            characters = get_entities_by_recency(Character, 20)
            for char in characters:
                char_info = {
                    "name": char.name,
                    "race": char.race.name if char.race else None,
                    "description": char.description[:100] if char.description else "",
                    "recently_mentioned": bool(
                        char.most_recent_log_date
                        and char.most_recent_log_date >= recent_threshold
                    ),
                }
                context["characters"].append(char_info)

            # Get Places
            places = get_entities_by_recency(Place, 15)
            for place in places:
                place_info = {
                    "name": place.name,
                    "type": getattr(place, "place_type", None),
                    "description": place.description[:100] if place.description else "",
                    "recently_mentioned": bool(
                        place.most_recent_log_date
                        and place.most_recent_log_date >= recent_threshold
                    ),
                }
                context["places"].append(place_info)

            # Get Races
            races = get_entities_by_recency(Race, 12)
            for race in races:
                race_info = {
                    "name": race.name,
                    "description": race.description[:100] if race.description else "",
                    "recently_mentioned": bool(
                        race.most_recent_log_date
                        and race.most_recent_log_date >= recent_threshold
                    ),
                }
                context["races"].append(race_info)

            # Get Items
            items = get_entities_by_recency(Item, 12)
            for item in items:
                item_info = {
                    "name": item.name,
                    "description": item.description[:80] if item.description else "",
                    "recently_mentioned": bool(
                        item.most_recent_log_date
                        and item.most_recent_log_date >= recent_threshold
                    ),
                }
                context["items"].append(item_info)

            # Get Artifacts
            artifacts = get_entities_by_recency(Artifact, 8)
            for artifact in artifacts:
                artifact_info = {
                    "name": artifact.name,
                    "type": "artifact",
                    "description": (
                        artifact.description[:80] if artifact.description else ""
                    ),
                    "recently_mentioned": bool(
                        artifact.most_recent_log_date
                        and artifact.most_recent_log_date >= recent_threshold
                    ),
                }
                context["items"].append(artifact_info)

            # Get Associations
            associations = get_entities_by_recency(Association, 12)
            for assoc in associations:
                assoc_info = {
                    "name": assoc.name,
                    "description": assoc.description[:100] if assoc.description else "",
                    "recently_mentioned": bool(
                        assoc.most_recent_log_date
                        and assoc.most_recent_log_date >= recent_threshold
                    ),
                }
                context["associations"].append(assoc_info)

        except Exception as e:
            print(f"Warning: Could not fetch database context: {e}")
            print("Continuing without database context...")

        return context

    def get_formatted_context(self, max_length: int = 800) -> str:
        """
        Get campaign context from database and format it for Whisper prompt.
        Prioritizes recently mentioned entities.
        """
        context = self.get_campaign_context()
        return self._format_context_for_prompt(context, max_length)

    def _format_context_for_prompt(
        self, context: Dict[str, List[Dict[str, Any]]], max_length: int = 1200
    ) -> str:
        """
        Format the campaign context into a concise string for the Whisper prompt.
        Prioritizes recently mentioned entities.
        """
        prompt_parts = []

        def get_prioritized_names(entities, max_count):
            """Sort by recently_mentioned first, then by name."""
            sorted_entities = sorted(
                entities,
                key=lambda x: (not x.get("recently_mentioned", False), x["name"]),
            )
            return [entity["name"] for entity in sorted_entities[:max_count]]

        # Character names (highest priority)
        if context["characters"]:
            recent_chars = []
            other_chars = []

            for char in context["characters"][:20]:
                name = char["name"]
                if char.get("race"):
                    name += f" ({char['race']})"

                if char.get("recently_mentioned"):
                    recent_chars.append(name)
                else:
                    other_chars.append(name)

            all_char_names = recent_chars[:10] + other_chars[:5]
            if all_char_names:
                prompt_parts.append(f"Key Characters: {', '.join(all_char_names)}")

        # Place names
        if context["places"]:
            place_names = get_prioritized_names(context["places"], 8)
            if place_names:
                prompt_parts.append(f"Important Places: {', '.join(place_names)}")

        # Race names
        if context["races"]:
            race_names = get_prioritized_names(context["races"], 8)
            if race_names:
                prompt_parts.append(f"Races: {', '.join(race_names)}")

        # Items/Artifacts
        if context["items"]:
            artifacts = [
                item for item in context["items"] if item.get("type") == "artifact"
            ]
            regular_items = [
                item for item in context["items"] if item.get("type") != "artifact"
            ]

            item_names = []
            if artifacts:
                artifact_names = get_prioritized_names(artifacts, 4)
                item_names.extend([f"{name} (artifact)" for name in artifact_names])

            if regular_items:
                regular_names = get_prioritized_names(regular_items, 6)
                item_names.extend(regular_names)

            if item_names:
                prompt_parts.append(f"Notable Items: {', '.join(item_names)}")

        # Organizations
        if context["associations"]:
            org_names = get_prioritized_names(context["associations"], 6)
            if org_names:
                prompt_parts.append(f"Organizations: {', '.join(org_names)}")

        # Join and truncate gracefully
        formatted_context = ". ".join(prompt_parts)

        # Handle edge case where max_length is 0 or very small
        if max_length <= 0:
            return ""

        if len(formatted_context) > max_length:
            if max_length < 10:  # Very small max_length
                return "..."

            truncated = formatted_context[:max_length]
            last_period = truncated.rfind(".")
            if last_period > max_length * 0.75:
                formatted_context = truncated[: last_period + 1]
            else:
                last_space = truncated.rfind(" ")
                if last_space > max_length * 0.9:
                    formatted_context = truncated[:last_space] + "..."
                else:
                    formatted_context = truncated + "..."

        return formatted_context


class AudioProcessingService:
    """Service for audio file processing and splitting."""

    def __init__(self, config: TranscriptionConfig):
        self.config = config

    @staticmethod
    def get_file_size_mb(file_path: Path) -> float:
        """Get file size in MB. Returns 0 if file doesn't exist."""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except (FileNotFoundError, OSError):
            return 0.0

    def preprocess_audio(
        self, audio: AudioSegment
    ) -> tuple[AudioSegment, List[Dict[str, float]]]:
        """
        Preprocess audio to reduce repetitive transcription issues while preserving timing information.

        Args:
            audio: AudioSegment to preprocess

        Returns:
            Tuple of (preprocessed_audio, time_offset_mapping)
            time_offset_mapping: List of dicts with 'original_start', 'original_end', 'processed_start', 'processed_end'
        """
        try:
            from pydub.silence import detect_silence

            # Store original audio length for reference
            original_duration_ms = len(audio)

            # Normalize audio levels to reduce volume inconsistencies
            # Use manual normalization since normalize() might not be available
            max_possible_val = audio.max_possible_amplitude
            current_max = audio.max
            if current_max > 0:
                normalization_factor = (
                    max_possible_val / current_max * 0.8
                )  # Don't max out
                audio = audio + (20 * math.log10(normalization_factor))

            # Apply noise reduction by detecting and removing very quiet segments
            # This helps prevent Whisper from hallucinating content in silent areas
            silence_threshold = int(audio.dBFS - 16)  # 16dB below average level

            # Detect silence periods to get exact timing information
            silence_ranges = detect_silence(
                audio,
                min_silence_len=2000,  # 2 seconds of silence
                silence_thresh=silence_threshold,
            )

            if silence_ranges:
                print(f"🔇 Detected {len(silence_ranges)} silence periods to remove")
                for i, (start, end) in enumerate(silence_ranges):
                    duration_s = (end - start) / 1000.0
                    print(
                        f"  Silence {i+1}: {start/1000.0:.2f}s - {end/1000.0:.2f}s ({duration_s:.2f}s)"
                    )

                # Build non-silent segments with exact timing
                time_offset_mapping = []
                processed_audio = AudioSegment.empty()
                processed_position_ms = 0

                # Create segments between silence periods
                segments = []
                last_end = 0

                for silence_start, silence_end in silence_ranges:
                    # Add the audio segment before this silence (if any)
                    if silence_start > last_end:
                        segments.append((last_end, silence_start))

                    # Skip the long silence, but keep a small gap
                    last_end = silence_end

                # Add the final segment after the last silence
                if last_end < original_duration_ms:
                    segments.append((last_end, original_duration_ms))

                # Process each non-silent segment
                for i, (segment_start, segment_end) in enumerate(segments):
                    # Extract the audio segment
                    segment_audio = audio[segment_start:segment_end]
                    segment_length_ms = segment_end - segment_start

                    print(
                        f"📄 Processing segment {i+1}: {segment_start/1000.0:.2f}s - {segment_end/1000.0:.2f}s ({segment_length_ms/1000.0:.2f}s)"
                    )

                    # Add some silence padding (keep_silence equivalent)
                    if processed_audio:  # Not the first segment
                        processed_audio += AudioSegment.silent(duration=500)
                        processed_position_ms += 500

                    # Add the segment to processed audio
                    processed_audio += segment_audio

                    # Create precise mapping entry
                    mapping_entry = {
                        "original_start": segment_start / 1000.0,  # Convert to seconds
                        "original_end": segment_end / 1000.0,
                        "processed_start": processed_position_ms / 1000.0,
                        "processed_end": (processed_position_ms + segment_length_ms)
                        / 1000.0,
                    }
                    time_offset_mapping.append(mapping_entry)

                    print(
                        f"  ⏱️  Mapping: Original {mapping_entry['original_start']:.2f}s-{mapping_entry['original_end']:.2f}s → Processed {mapping_entry['processed_start']:.2f}s-{mapping_entry['processed_end']:.2f}s"
                    )

                    processed_position_ms += segment_length_ms

                total_original_ms = original_duration_ms
                total_processed_ms = len(processed_audio)
                time_saved_ms = total_original_ms - total_processed_ms

                print(f"✅ Audio preprocessing complete:")
                print(f"   Original: {total_original_ms/1000.0:.2f}s")
                print(f"   Processed: {total_processed_ms/1000.0:.2f}s")
                print(
                    f"   Time saved: {time_saved_ms/1000.0:.2f}s ({time_saved_ms/total_original_ms*100:.1f}%)"
                )
                print(f"   Created {len(time_offset_mapping)} segment mappings")

                return processed_audio, time_offset_mapping
            else:
                # No silence detected, return original with identity mapping
                identity_mapping = [
                    {
                        "original_start": 0.0,
                        "original_end": original_duration_ms / 1000.0,
                        "processed_start": 0.0,
                        "processed_end": original_duration_ms / 1000.0,
                    }
                ]
                return audio, identity_mapping

        except Exception as e:
            print(f"⚠️ Audio preprocessing failed: {e}, using original audio")
            # Return original audio with identity mapping
            original_duration_ms = len(audio)
            identity_mapping = [
                {
                    "original_start": 0.0,
                    "original_end": original_duration_ms / 1000.0,
                    "processed_start": 0.0,
                    "processed_end": original_duration_ms / 1000.0,
                }
            ]
            return audio, identity_mapping

    @staticmethod
    def convert_processed_to_original_timestamp(
        processed_time: float, time_offset_mapping: List[Dict[str, float]]
    ) -> float:
        """
        Convert a timestamp from processed audio back to original audio timeline.

        Args:
            processed_time: Time in seconds from the processed audio
            time_offset_mapping: The mapping created during preprocessing

        Returns:
            Corresponding time in the original audio timeline
        """
        if not time_offset_mapping:
            return processed_time

        # Find the mapping segment that contains this processed time
        for mapping in time_offset_mapping:
            if mapping["processed_start"] <= processed_time <= mapping["processed_end"]:
                # Calculate relative position within the segment
                segment_progress = (processed_time - mapping["processed_start"]) / (
                    mapping["processed_end"] - mapping["processed_start"]
                )

                # Apply to original timeline
                original_duration = mapping["original_end"] - mapping["original_start"]
                original_time = mapping["original_start"] + (
                    segment_progress * original_duration
                )

                return original_time

        # If not found in any segment, return the processed time as fallback
        return processed_time

    def split_audio_file(
        self, file_path: Path, character_name: str = "Unknown"
    ) -> Tuple[List[Path], List[Dict]]:
        """
        Split an audio file into chunks if it exceeds the size limit.
        Returns a list of chunk file paths.
        """
        import tempfile

        file_size_mb = AudioProcessingService.get_file_size_mb(file_path)

        try:
            audio = AudioSegment.from_file(file_path)
            time_offset_mapping = None

            # If file is within size limit, preprocess and return single file
            if file_size_mb <= self.config.max_file_size_mb:
                # Only preprocess audio for single files to get time offset mapping
                if self.config.enable_audio_preprocessing:
                    audio, time_offset_mapping = self.preprocess_audio(audio)
                    
                print(
                    f"✅ {file_path.name} ({file_size_mb:.1f}MB) is within size limit"
                )

                # Create metadata entry for the single file
                metadata = [
                    {
                        "path": file_path,
                        "start_time_ms": 0,
                        "end_time_ms": len(audio),
                        "time_offset_mapping": time_offset_mapping,
                    }
                ]
                return [file_path], metadata

            print(
                f"📂 Splitting {file_path.name} ({file_size_mb:.1f}MB) into chunks..."
            )
            print(f"   ⚠️ Skipping audio preprocessing for chunked files to improve performance")

            chunk_length_ms = self.config.chunk_duration_minutes * 60 * 1000
            total_length_ms = len(audio)
            num_chunks = math.ceil(total_length_ms / chunk_length_ms)

            chunk_paths = []
            chunk_metadata = []  # Store metadata including time offset mappings

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                for i in range(num_chunks):
                    start_time = i * chunk_length_ms
                    end_time = min((i + 1) * chunk_length_ms, total_length_ms)

                    chunk = audio[start_time:end_time]
                    chunk_filename = f"{file_path.stem}_{character_name}_chunk_{i+1:02d}{file_path.suffix}"
                    chunk_path = temp_dir_path / chunk_filename

                    chunk.export(chunk_path, format=file_path.suffix[1:])

                    chunk_size_mb = AudioProcessingService.get_file_size_mb(chunk_path)
                    print(f"  ✅ Created {chunk_filename} ({chunk_size_mb:.1f}MB)")

                    # Store chunk metadata without time offset mapping (not applicable for chunks)
                    chunk_info = {
                        "path": chunk_path,
                        "start_time_ms": start_time,
                        "end_time_ms": end_time,
                        "time_offset_mapping": None,  # No preprocessing for chunks
                    }
                    chunk_metadata.append(chunk_info)
                    chunk_paths.append(chunk_path)

                # Copy chunk files to a list of paths outside the context manager
                result_paths = []
                result_metadata = []
                for i, chunk_path in enumerate(chunk_paths):
                    # Move to a new NamedTemporaryFile to persist after context
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=file_path.suffix
                    ) as f:
                        f.write(chunk_path.read_bytes())
                        result_paths.append(Path(f.name))

                        # Update metadata with the new path
                        updated_metadata = chunk_metadata[i].copy()
                        updated_metadata["path"] = Path(f.name)
                        result_metadata.append(updated_metadata)

                return result_paths, result_metadata

        except Exception as e:
            print(f"❌ Failed to split {file_path.name}: {e}")
            return [file_path], []


class TranscriptionService:
    """Main service for transcribing D&D audio files with campaign context."""

    def __init__(self, config: Optional[TranscriptionConfig] = None):
        self.config = config or TranscriptionConfig()

        if not self.config.openai_api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in settings or environment."
            )

        openai.api_key = self.config.openai_api_key

        self.context_service = CampaignContextService(self.config)
        self.audio_service = AudioProcessingService(self.config)

    def process_session_audio(
        self,
        session_audio: SessionAudio,
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> bool:
        """Process a SessionAudio instance, split if needed, and save all results to the database."""
        import tempfile

        start_time = time.time()
        temp_path = None
        chunk_paths = []

        try:
            file_name = (
                getattr(session_audio, "original_filename", None)
                or Path(session_audio.file.name).name
            )

            # Save the uploaded file to a temp file for processing
            with tempfile.NamedTemporaryFile(
                suffix=Path(session_audio.file.name).suffix, delete=False
            ) as temp_file:
                for chunk in session_audio.file.chunks():
                    temp_file.write(chunk)
                temp_path = Path(temp_file.name)

            file_size_mb = AudioProcessingService.get_file_size_mb(temp_path)
            print(f"Processing {file_name} ({file_size_mb:.1f}MB)...")

            # Split file if needed
            chunk_paths, chunk_metadata = self.audio_service.split_audio_file(
                temp_path, Path(file_name).stem
            )

            if len(chunk_paths) == 1:
                # File wasn't split, get time_offset_mapping from metadata
                time_offset_mapping = None
                if chunk_metadata and chunk_metadata[0].get("time_offset_mapping"):
                    time_offset_mapping = chunk_metadata[0]["time_offset_mapping"]

                whisper_response = self._call_whisper_api(
                    temp_path,
                    character_name=Path(file_name).stem,
                    previous_transcript=previous_transcript,
                    session_notes=session_notes,
                )

                if whisper_response:
                    # Calculate processing time
                    processing_time = time.time() - start_time

                    # Save to database with time offset mapping if available
                    self._save_audio_transcript(
                        session_audio=session_audio,
                        file_path=temp_path,
                        character_name=Path(file_name).stem,
                        file_size_mb=file_size_mb,
                        whisper_response=whisper_response,
                        was_split=False,
                        num_chunks=1,
                        processing_time=processing_time,
                        time_offset_mapping=time_offset_mapping,
                    )

                    print(f"✅ Successfully processed {file_name} in {processing_time:.1f}s")
                    return True
                else:
                    print(f"❌ Failed to transcribe {file_name}")
                    return False
            else:
                # File was split, transcribe chunks and save all outputs
                combined_transcript = self._process_chunks(
                    chunk_paths,
                    character_name=Path(file_name).stem,
                    previous_transcript=previous_transcript,
                    session_notes=session_notes,
                )

                if combined_transcript:
                    # Calculate processing time
                    processing_time = time.time() - start_time

                    # Extract and combine time offset mapping from chunk metadata
                    combined_time_offset_mapping = None
                    if chunk_metadata and any(
                        metadata.get("time_offset_mapping") for metadata in chunk_metadata
                    ):
                        combined_time_offset_mapping = []
                        chunk_duration_s = self.config.chunk_duration_minutes * 60

                        for i, metadata in enumerate(chunk_metadata):
                            chunk_mapping = metadata.get("time_offset_mapping")
                            if chunk_mapping:
                                # Adjust the mapping to account for chunk position in the overall file
                                chunk_start_offset = i * chunk_duration_s
                                for mapping_entry in chunk_mapping:
                                    adjusted_entry = {
                                        "original_start": mapping_entry["original_start"]
                                        + chunk_start_offset,
                                        "original_end": mapping_entry["original_end"]
                                        + chunk_start_offset,
                                        "processed_start": mapping_entry["processed_start"]
                                        + i
                                        * chunk_duration_s,  # Processed chunks maintain sequential timing
                                        "processed_end": mapping_entry["processed_end"]
                                        + i * chunk_duration_s,
                                    }
                                    combined_time_offset_mapping.append(adjusted_entry)

                    # Save to database
                    audio_transcript = self._save_audio_transcript(
                        session_audio=session_audio,
                        file_path=temp_path,
                        character_name=Path(file_name).stem,
                        file_size_mb=file_size_mb,
                        whisper_response=combined_transcript,
                        was_split=True,
                        num_chunks=len(chunk_paths),
                        processing_time=processing_time,
                        time_offset_mapping=combined_time_offset_mapping,
                    )

                    # Save chunk data to database
                    self._save_transcript_chunks(
                        audio_transcript, combined_transcript, chunk_paths
                    )

                    print(f"✅ Successfully processed {file_name} ({len(chunk_paths)} chunks) in {processing_time:.1f}s")
                    return True
                else:
                    print(f"❌ Failed to process chunks for {file_name}")
                    return False

        except Exception as e:
            print(f"❌ Error processing {session_audio}: {e}")
            return False

        finally:
            # Clean up temporary files
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    print(f"🗑️ Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    print(f"⚠️ Failed to clean up temporary file {temp_path}: {e}")

            # Clean up chunk files if they were created
            for chunk_path in chunk_paths:
                if chunk_path and chunk_path.exists():
                    try:
                        chunk_path.unlink()
                        print(f"🗑️ Cleaned up chunk file: {chunk_path}")
                    except Exception as e:
                        print(f"⚠️ Failed to clean up chunk file {chunk_path}: {e}")

    # ========================================
    # Database Operations
    # ========================================

    def _save_audio_transcript(
        self,
        session_audio: SessionAudio,
        file_path: Path,
        character_name: str,
        file_size_mb: float,
        whisper_response,
        was_split: bool,
        num_chunks: int,
        processing_time: float,
        time_offset_mapping: Optional[List[Dict[str, float]]] = None,
    ) -> AudioTranscript:
        """Save audio transcript data to database."""
        from .responses import WhisperResponse

        # Handle both WhisperResponse objects and raw dict responses
        if isinstance(whisper_response, WhisperResponse):
            transcript_text = whisper_response.text
            raw_response = whisper_response.raw_response
        else:
            # For combined transcripts (dict)
            transcript_text = whisper_response.get("text", "")
            raw_response = whisper_response

        # Clean repetitive patterns from transcript text
        if transcript_text and self.config.enable_text_cleaning:
            transcript_text = TranscriptCleaner.clean_repetitive_text(
                transcript_text, max_repetitions=self.config.max_allowed_repetitions
            )

        # Get campaign context that was used
        campaign_context = self.context_service.get_campaign_context()

        # Calculate duration from whisper response if available
        duration_minutes = None
        if isinstance(raw_response, dict) and "segments" in raw_response:
            segments = raw_response["segments"]
            if segments:
                last_segment = max(segments, key=lambda s: s.get("end", 0))
                duration_minutes = last_segment.get("end", 0) / 60

        # If we have time offset mapping, convert segment timestamps back to original timeline
        adjusted_segments = None
        if (
            time_offset_mapping
            and isinstance(raw_response, dict)
            and "segments" in raw_response
        ):
            adjusted_segments = []
            for segment in raw_response["segments"]:
                adjusted_segment = segment.copy()
                adjusted_segment["start"] = (
                    AudioProcessingService.convert_processed_to_original_timestamp(
                        segment["start"], time_offset_mapping
                    )
                )
                adjusted_segment["end"] = (
                    AudioProcessingService.convert_processed_to_original_timestamp(
                        segment["end"], time_offset_mapping
                    )
                )
                adjusted_segments.append(adjusted_segment)

            # Update the raw response with adjusted timestamps
            raw_response = raw_response.copy()
            raw_response["segments"] = adjusted_segments
            raw_response["time_offset_mapping"] = time_offset_mapping

        audio_transcript = AudioTranscript.objects.create(
            session_audio=session_audio,
            original_filename=file_path.name,
            character_name=character_name,
            file_size_mb=file_size_mb,
            duration_minutes=duration_minutes,
            transcript_text=transcript_text,
            whisper_response=raw_response,
            was_split=was_split,
            num_chunks=num_chunks,
            processing_time_seconds=processing_time,
            campaign_context=campaign_context,
        )

        print(f"✅ Saved audio transcript to database: {audio_transcript}")
        return audio_transcript

    def _save_transcript_chunks(
        self,
        audio_transcript: AudioTranscript,
        combined_transcript: dict,
        chunk_paths: List[Path],
    ):
        """Save individual chunk data to database."""
        chunk_transcripts = combined_transcript.get("chunks", [])

        for i, (chunk_path, chunk_transcript) in enumerate(
            zip(chunk_paths, chunk_transcripts)
        ):
            from .responses import WhisperResponse

            # Extract chunk data - chunk_transcript is already the raw transcript data
            whisper_response = WhisperResponse(chunk_transcript)
            chunk_text = whisper_response.text

            # Calculate chunk timing
            start_time_offset = i * self.config.chunk_duration_minutes * 60

            # Get duration from segments if available
            duration_seconds = self.config.chunk_duration_minutes * 60  # Default
            if whisper_response.segments:
                last_segment = max(
                    whisper_response.segments, key=lambda s: s.get("end", 0)
                )
                duration_seconds = last_segment.get("end", duration_seconds)

            TranscriptChunk.objects.create(
                transcript=audio_transcript,
                chunk_number=i + 1,
                filename=chunk_path.name,
                start_time_offset=start_time_offset,
                duration_seconds=duration_seconds,
                chunk_text=chunk_text,
                whisper_response=chunk_transcript,
            )

        print(f"✅ Saved {len(chunk_transcripts)} transcript chunks to database")

    # ========================================
    # Private Implementation Methods
    # ========================================

    def _create_whisper_prompt(
        self,
        character_name: str,
        chunk_info: str = "",
        previous_chunks_text: str = "",
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> str:
        """Create a comprehensive prompt for Whisper API."""

        # Calculate context components in order of usage for logical flow
        # 1. Character identification with chunk context (immediate context)
        character_display = "the DM" if character_name == "DM" else character_name
        if chunk_info:
            character_chunk_info = (
                f"This is {character_display} and this is {chunk_info}"
            )
        else:
            character_chunk_info = f"This is {character_display}"

        # 2. Session-specific context (current session details)
        session_context = f" {session_notes}" if session_notes else ""

        # 4. Campaign context (broader world knowledge)
        formatted_context = self.context_service.get_formatted_context(max_length=800)
        campaign_context = (
            f"\n\nCampaign Context: {formatted_context}" if formatted_context else ""
        )

        # 5. Previous transcript context (historical session data)
        transcript_context = (
            f"\n\nPrevious Transcript:\n{previous_transcript}"
            if previous_transcript
            else ""
        )

        # 6. Recent chunks context (immediate previous processing context)
        recent_chunks_context = ""
        if previous_chunks_text:
            words = previous_chunks_text.split()
            if len(words) > 500:
                previous_chunks_text = " ".join(words[-500:])
            recent_chunks_context = f"\n\nRecent chunks from this session for {character_name}:\n{previous_chunks_text}"

        # Build complete prompt in logical context flow order
        full_prompt = (
            f"This is a session of a homebrew Dungeons & Dragons game. The player characters include "
            f"Darnit, Hrothulf, Ego (aka Carlos), Izar, and Dorinda. "
            f"The last session's transcript is provided below, followed by any chunks transcribed thus far for this player. "
            f"Distinguish between narration, banter, and in-character dialogue when possible. "
            f"{character_chunk_info}.{session_context}"
            f"{campaign_context}"
            f"{transcript_context}"
            f"{recent_chunks_context}"
        )

        return full_prompt

    def _call_whisper_api(
        self,
        file_path: Path,
        character_name: str,
        chunk_info: str = "",
        previous_chunks_text: str = "",
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> Optional[WhisperResponse]:
        """Make a Whisper API call with validation and error handling."""
        try:
            with file_path.open("rb") as f:
                print(f"Transcribing {file_path.name}...")
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    prompt=self._create_whisper_prompt(
                        character_name,
                        chunk_info,
                        previous_chunks_text,
                        previous_transcript,
                        session_notes,
                    ),
                    temperature=0,  # Keep low to reduce hallucinations
                    language="en",
                )

                # Validate response structure using WhisperResponse
                whisper_response = WhisperResponse(response)
                if not whisper_response.is_valid:
                    print(
                        f"⚠️ Invalid response format from Whisper API for {file_path.name}"
                    )
                    return None

                # Check for low quality output and retry with different parameters if needed
                if TranscriptCleaner.detect_low_quality_segments(
                    whisper_response.text,
                    threshold=self.config.repetition_detection_threshold,
                ):
                    print(
                        f"⚠️ Low quality transcript detected for {file_path.name}, retrying with no prompt..."
                    )
                    # Reset file pointer to beginning before retry
                    f.seek(0)
                    
                    # Retry without prompt to reduce hallucinations
                    response = openai.Audio.transcribe(
                        model="whisper-1",
                        file=f,
                        response_format="verbose_json",
                        temperature=0,
                        language="en",
                    )
                    whisper_response = WhisperResponse(response)

                return whisper_response

        except Exception as e:
            print(f"❌ Failed to transcribe {file_path.name}: {e}")
            return None

    def _process_chunks(
        self,
        chunk_paths: List[Path],
        character_name: str,
        previous_transcript: str,
        session_notes: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Process multiple audio chunks and return combined transcript data. Pure function - no file I/O."""
        all_transcripts = []
        previous_chunks_text = ""

        for i, chunk_path in enumerate(chunk_paths):
            chunk_info = f"the {ordinal(i+1)} chunk of {len(chunk_paths)}"

            whisper_response = self._call_whisper_api(
                chunk_path,
                character_name,
                chunk_info,
                previous_chunks_text,
                previous_transcript,
                session_notes,
            )

            if whisper_response:
                # Collect transcripts for processing
                all_transcripts.append(
                    {
                        "transcript": whisper_response.raw_response,
                        "chunk_path": chunk_path,
                    }
                )

                # Update previous chunks text for subsequent chunk prompts
                chunk_text = whisper_response.text
                if chunk_text:
                    previous_chunks_text += f"\n\n{chunk_text}"

                # Delay between requests
                if i < len(chunk_paths) - 1:
                    time.sleep(self.config.delay_between_requests)

        # Return combined transcript data (no file I/O)
        if all_transcripts:
            return self._create_combined_transcript(
                [item["transcript"] for item in all_transcripts]
            )

        return None

    def _create_combined_transcript(
        self, all_transcripts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Create a combined transcript from multiple chunks. Pure function - no side effects."""
        try:
            # Safely extract text from all transcripts
            text_parts = []
            for transcript in all_transcripts:
                whisper_response = WhisperResponse(transcript)
                text = whisper_response.text
                if text:
                    text_parts.append(text)

            combined_text = "\n\n".join(text_parts)
            combined_transcript = {
                "text": combined_text,
                "segments": [],
                "chunks": all_transcripts,
            }

            # Combine segments with time offsets
            time_offset = 0
            for transcript in all_transcripts:
                whisper_response = WhisperResponse(transcript)
                segments = whisper_response.segments
                for segment in segments:
                    adjusted_segment = segment.copy()
                    adjusted_segment["start"] += time_offset
                    adjusted_segment["end"] += time_offset
                    combined_transcript["segments"].append(adjusted_segment)

                time_offset += self.config.chunk_duration_minutes * 60

            return combined_transcript

        except Exception as e:
            print(f"❌ Failed to create combined transcript: {e}")
            return None

    @staticmethod
    def make_concat_prompt(gamelog: GameLog) -> str:
        """
        Generate the LLM prompt using the concatenated transcript approach.
        """
        from transcription.models import AudioTranscript

        # Get the previous GameLog by game_date (excluding this one)
        previous_log = gamelog.get_previous_log()
        example_section = ""
        if previous_log and previous_log.log_text and previous_log.log_text.strip():
            example_section = (
                "\n\nThe following is the log from the previous session. Please use a similar style and maintain narrative continuity in the new session log.\n"
                f"Previous session log:\n{previous_log.log_text}\n"
            )

        transcripts = AudioTranscript.objects.filter(
            session_audio__gamelog=gamelog
        ).order_by("session_audio__id")
        if not transcripts.exists():
            return ""
        combined = "\n".join(
            f"[{t.character_name}] {t.transcript_text.strip()}"
            for t in transcripts
            if t.transcript_text.strip()
        )
        session_notes = gamelog.audio_session_notes or ""
        notes_section = (
            f"\n\nSession notes for context (important anomalies, DM/player issues, etc.):\n{session_notes}\n"
            if session_notes
            else ""
        )
        prompt = f"""
You are a Dungeons & Dragons session chronicler. Given the following raw transcripts from multiple players, produce a single, clean, in-game session log. 
- Remove all out-of-character banter, rules discussion, and non-game chatter.
- Attribute dialogue to characters (e.g., 'Izar said, \"Let's attack!\"').
- Write narration and events as they unfold in the story.
- Do not mention player names or much meta-discussion.
- The result should read as a narrative of the session, as if it were a story or campaign log.
- Do not summarize or embellish. Give the session log in full, as it is in the transcripts.
- The main players and characters are as follows: Greg is the DM; Noel plays Izar; Scott plays Ego aka Carlos; MJ aka Michael plays Hrothulf; Wes plays Darnit; Joel plays Dorinda.
{notes_section}
{example_section}
Raw transcripts:
{combined}

Session log:
"""
        return prompt

    @staticmethod
    def make_segment_prompt(gamelog: GameLog) -> str:
        """
        Generate the LLM prompt using the segment-based, time-ordered approach.
        """
        from transcription.models import AudioTranscript

        # Get the previous GameLog by game_date (excluding this one)
        previous_log = gamelog.get_previous_log()
        example_section = ""
        if previous_log and previous_log.log_text and previous_log.log_text.strip():
            example_section = (
                "\n\nThe following is the log from the previous session. Please use a similar style and maintain narrative continuity in the new session log.\n"
                f"Previous session log:\n{previous_log.log_text}\n"
            )

        transcripts = AudioTranscript.objects.filter(session_audio__gamelog=gamelog)
        if not transcripts.exists():
            return ""
        segments = []
        for t in transcripts:
            whisper = t.whisper_response or {}
            time_offset_mapping = whisper.get("time_offset_mapping")

            for seg in whisper.get("segments", []):
                # Use original timestamps if available, otherwise use the segment timestamps as-is
                segment_start = seg.get("start", 0)
                segment_end = seg.get("end", 0)

                # If we have time offset mapping, the timestamps should already be converted
                # during the save process, so we can use them directly

                segments.append(
                    {
                        "start": segment_start,
                        "end": segment_end,
                        "text": seg.get("text", "").strip(),
                        "character": t.character_name,
                    }
                )
        segments.sort(key=lambda s: s["start"])

        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h:02}:{m:02}:{s:02}"

        combined = "\n".join(
            f"[{format_time(seg['start'])}] [{seg['character']}] {seg['text']}"
            for seg in segments
            if seg["text"]
        )
        session_notes = gamelog.audio_session_notes or ""
        notes_section = (
            f"\n\nSession notes for context (important anomalies, DM/player issues, etc.):\n{session_notes}\n"
            if session_notes
            else ""
        )
        prompt = f"""
You are a Dungeons & Dragons session chronicler. Given the following time-ordered, attributed transcript segments, produce a single, clean, in-game session log. 
- Remove all out-of-character banter, rules discussion, and non-game chatter.
- Attribute dialogue to characters (e.g., 'Izar said, \"Let's attack!\"').
- Write narration and events as they unfold in the story.
- Do not mention player names or much meta-discussion.
- The result should read as a narrative of the session, as if it were a story or campaign log.
- Do not summarize or embellish. Give the session log in full, as it is in the transcripts.
- The main players and characters are as follows: Greg is the DM; Noel plays Izar; Scott plays Ego aka Carlos; MJ aka Michael plays Hrothulf; Wes plays Darnit; Joel plays Dorinda.
{notes_section}
{example_section}
Time-ordered transcript segments:
{combined}

Session log:
"""
        return prompt

    @staticmethod
    def generate_session_log_from_transcripts(
        gamelog: GameLog, model: str = "gpt-4o", method: str = "concat"
    ) -> str:
        """
        Generate a session log using either the 'concat' or 'segment' method. Shared OpenAI logic.
        """
        import openai

        if method == "segment":
            prompt = TranscriptionService.make_segment_prompt(gamelog)
        else:
            prompt = TranscriptionService.make_concat_prompt(gamelog)
        if not prompt.strip():
            return ""
        print(f"Generating session log for {gamelog} using {method} method...")
        print(f"Prompt length: {len(prompt)} characters")
        print("prompt:", prompt)
        import tiktoken

        encoding = tiktoken.encoding_for_model(model)
        num_tokens = len(encoding.encode(prompt))
        print(f"Estimated token count: {num_tokens} tokens")
        # response = openai.ChatCompletion.create(
        #     model=model,
        #     messages=[{"role": "user", "content": prompt}],
        #     temperature=0.3,
        #     max_tokens=3500,
        # )
        # session_log = response["choices"][0]["message"]["content"].strip()
        # gamelog.generated_log_text = session_log
        # gamelog.save(update_fields=["generated_log_text"])
        # return session_log

    def _is_large_processing_job(self, session_audio) -> bool:
        """
        Determine if this is likely a large processing job that should use Celery.

        Args:
            session_audio: SessionAudio instance to evaluate

        Returns:
            True if this appears to be a large job that should use async processing
        """
        try:
            # If file size is available, use that as the primary indicator
            if hasattr(session_audio, "file") and session_audio.file:
                file_size_mb = session_audio.file.size / (1024 * 1024)
                # Files larger than 50MB are likely to be long audio files
                if file_size_mb > 50:
                    return True

            # Check if the filename suggests it's a long recording
            filename = getattr(session_audio, "original_filename", "") or str(
                session_audio.file.name if hasattr(session_audio, "file") else ""
            )
            filename_lower = filename.lower()

            # Look for indicators of long recordings in filename
            long_indicators = ["hour", "session", "full", "complete", "entire"]
            if any(indicator in filename_lower for indicator in long_indicators):
                return True

            return False
        except Exception:
            # If we can't determine file size, err on the side of caution
            return True

    def process_session_audio_async(
        self,
        session_audio: SessionAudio,
        previous_transcript: str = "",
        session_notes: str = "",
        use_celery: bool = True,
    ):
        print("process_session_audio_async called with use_celery =", use_celery)
        """
        Process a SessionAudio instance asynchronously using Celery.

        Args:
            session_audio: The SessionAudio instance to process
            previous_transcript: Previous transcript text for context
            session_notes: Session notes for context
            use_celery: Whether to use Celery for async processing

        Returns:
            AsyncResult if using Celery, otherwise result of synchronous processing
        """
        if use_celery:
            try:
                from .tasks import process_session_audio_task

                print(".   about to call process_session_audio_task.delay_on_commit")

                return process_session_audio_task.delay_on_commit(
                    session_audio.id, previous_transcript, session_notes
                )
            except ImportError:
                # Check if this might be a large processing job that should use Celery
                if self._is_large_processing_job(session_audio):
                    raise RuntimeError(
                        "Celery is not available, but this appears to be a large audio processing job "
                        "that may take a very long time or fail when processed synchronously. "
                        "Please ensure Celery workers are running for large file processing. "
                        "You can start a worker with: celery -A website worker --loglevel=info"
                    )

                # Fallback to synchronous processing for smaller files
                return self.process_session_audio(
                    session_audio, previous_transcript, session_notes
                )
        else:
            return self.process_session_audio(
                session_audio, previous_transcript, session_notes
            )

    def generate_session_log_async(
        self,
        gamelog,
        method: str = "concat",
        model: str = "gpt-4o",
        use_celery: bool = True,
    ):
        """
        Generate a session log asynchronously using Celery.

        Args:
            gamelog: The GameLog instance
            method: Method to use for log generation ('concat' or 'segment')
            model: OpenAI model to use
            use_celery: Whether to use Celery for async processing

        Returns:
            AsyncResult if using Celery, otherwise result of synchronous processing
        """
        if use_celery:
            try:
                from .tasks import generate_session_log_task

                return generate_session_log_task.delay_on_commit(
                    gamelog.id, method, model
                )
            except ImportError:
                # Fallback to synchronous processing if Celery is not available
                return self.generate_session_log_from_transcripts(
                    gamelog, model, method
                )
        else:
            return self.generate_session_log_from_transcripts(gamelog, model, method)


def transcribe_session_audio(
    session_audio: SessionAudio,
    session_notes: str = "",
    previous_transcript: str = "",
    use_celery: bool = True,
):
    print("transcribe_session_audio called with use_celery =", use_celery)
    """
    Process a SessionAudio instance using the model-driven transcription logic.
    By default, uses async processing via Celery for better performance and scalability.

    Args:
        session_audio: The SessionAudio instance to process
        session_notes: Session notes for context
        previous_transcript: Previous transcript text for context
        use_celery: Whether to use Celery for async processing (default: True)

    Returns:
        AsyncResult if using Celery, otherwise boolean result of synchronous processing
    """
    service = TranscriptionService()
    return service.process_session_audio_async(
        session_audio,
        previous_transcript=previous_transcript,
        session_notes=session_notes,
        use_celery=use_celery,
    )
