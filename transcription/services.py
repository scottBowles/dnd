"""
Transcription services for D&D audio files.
Provides Whisper API integration with campaign-specific context enhancement.
"""

import math
import os
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import openai
from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from pydub import AudioSegment

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from place.models import Place
from race.models import Race

from .responses import WhisperResponse
from .utils import ordinal, safe_save_json


class TranscriptionConfig:
    """Configuration settings for transcription service."""

    def __init__(
        self,
        input_folder: Optional[Path] = None,
        output_folder: Optional[Path] = None,
        chunks_folder: Optional[Path] = None,
        max_file_size_mb: int = 20,
        chunk_duration_minutes: int = 10,
        delay_between_requests: int = 21,
        recent_threshold_days: int = 180,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize configuration with optional custom paths."""

        # API Configuration
        self.openai_api_key = openai_api_key or getattr(
            settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")
        )

        # File Processing
        self.max_file_size_mb = max_file_size_mb  # Buffer under 25MB Whisper limit
        self.chunk_duration_minutes = chunk_duration_minutes
        self.audio_extensions = [".flac", ".wav", ".aac", ".m4a", ".mp3"]

        # Directories (can be customized per instance)
        self.input_folder = input_folder or Path("recordings")
        self._output_folder = output_folder or Path("transcripts")
        self._chunks_folder = chunks_folder or Path("audio_chunks")

        # API Settings
        self.delay_between_requests = delay_between_requests  # seconds
        self.recent_threshold_days = recent_threshold_days  # 6 months

    @property
    def output_folder(self) -> Path:
        """Output folder for transcripts (created on first access)."""
        self._output_folder.mkdir(parents=True, exist_ok=True)
        return self._output_folder

    @property
    def chunks_folder(self) -> Path:
        """Chunks folder for temporary audio files (created on first access)."""
        self._chunks_folder.mkdir(parents=True, exist_ok=True)
        return self._chunks_folder


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
                formatted_context = truncated[:last_period + 1]
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
        """Initialize with configuration instance."""
        self.config = config

    @staticmethod
    def get_file_size_mb(file_path: Path) -> float:
        """Get file size in MB. Returns 0 if file doesn't exist."""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except (FileNotFoundError, OSError):
            return 0.0

    def split_audio_file(
        self, file_path: Path, character_name: str = "Unknown"
    ) -> List[Path]:
        """
        Split an audio file into chunks if it exceeds the size limit.
        Returns a list of chunk file paths.
        """
        file_size_mb = AudioProcessingService.get_file_size_mb(file_path)

        if file_size_mb <= self.config.max_file_size_mb:
            print(f"✅ {file_path.name} ({file_size_mb:.1f}MB) is within size limit")
            return [file_path]

        print(f"📂 Splitting {file_path.name} ({file_size_mb:.1f}MB) into chunks...")

        try:
            audio = AudioSegment.from_file(file_path)
            chunk_length_ms = self.config.chunk_duration_minutes * 60 * 1000
            total_length_ms = len(audio)
            num_chunks = math.ceil(total_length_ms / chunk_length_ms)

            chunk_paths = []

            for i in range(num_chunks):
                start_time = i * chunk_length_ms
                end_time = min((i + 1) * chunk_length_ms, total_length_ms)

                chunk = audio[start_time:end_time]
                chunk_filename = f"{file_path.stem}_{character_name}_chunk_{i+1:02d}{file_path.suffix}"
                chunk_path = self.config.chunks_folder / chunk_filename

                chunk.export(chunk_path, format=file_path.suffix[1:])

                chunk_size_mb = AudioProcessingService.get_file_size_mb(chunk_path)
                print(f"  ✅ Created {chunk_filename} ({chunk_size_mb:.1f}MB)")
                chunk_paths.append(chunk_path)

            print(f"✅ Split into {num_chunks} chunks")
            return chunk_paths

        except Exception as e:
            print(f"❌ Failed to split {file_path.name}: {e}")
            return [file_path]


class TranscriptionService:
    """Main service for transcribing D&D audio files with campaign context."""

    def __init__(self, config: Optional[TranscriptionConfig] = None):
        """Initialize with configuration instance."""
        self.config = config or TranscriptionConfig()

        if not self.config.openai_api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in settings or environment."
            )

        openai.api_key = self.config.openai_api_key

        self.context_service = CampaignContextService(self.config)
        self.audio_service = AudioProcessingService(self.config)

    # ========================================
    # Public Interface Methods
    # ========================================

    def process_file_with_splitting(
        self,
        file_path: Path,
        session_number: int = 1,
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> bool:
        """Process a file, splitting it if necessary, and transcribe all chunks."""
        character_name = file_path.stem

        # Check if already transcribed
        final_output = self.config.output_folder / file_path.with_suffix(".json").name
        if final_output.exists():
            print(f"✅ Already transcribed: {file_path.name}")
            return True

        # Split file if needed
        chunk_paths = self.audio_service.split_audio_file(file_path, character_name)

        if len(chunk_paths) == 1:
            # File wasn't split, transcribe directly and save
            whisper_response = self._call_whisper_api(
                file_path,
                character_name,
                session_number,
                previous_transcript=previous_transcript,
                session_notes=session_notes,
            )

            if whisper_response:
                return safe_save_json(
                    whisper_response.raw_response, final_output, "transcript"
                )
            return False
        else:
            # File was split, transcribe chunks and save all outputs
            combined_transcript = self._process_chunks(
                chunk_paths,
                character_name,
                session_number,
                previous_transcript,
                session_notes,
            )

            if combined_transcript:
                # Save individual chunk transcripts (extracted from combined data)
                chunk_transcripts = combined_transcript.get("chunks", [])
                for i, (chunk_path, chunk_transcript) in enumerate(
                    zip(chunk_paths, chunk_transcripts)
                ):
                    chunk_output = (
                        self.config.output_folder / chunk_path.with_suffix(".json").name
                    )
                    safe_save_json(chunk_transcript, chunk_output, f"chunk transcript")

                # Save combined transcript
                return safe_save_json(
                    combined_transcript, final_output, "combined transcript"
                )

            return False

    def process_all_files(
        self,
        session_number: int = 1,
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> int:
        """Process all audio files in the input folder."""
        processed_count = 0

        for file in self.config.input_folder.iterdir():
            if file.suffix.lower() in self.config.audio_extensions:
                if self.process_file_with_splitting(
                    file, session_number, previous_transcript, session_notes
                ):
                    processed_count += 1

        return processed_count

    # ========================================
    # Private Implementation Methods
    # ========================================

    def _create_whisper_prompt(
        self,
        character_name: str,
        session_number: int,
        chunk_info: str = "",
        previous_chunks_text: str = "",
        previous_transcript: str = "",
        session_notes: str = "",
    ) -> str:
        """Create a comprehensive prompt for Whisper API."""

        # Calculate context components in order of usage for logical flow
        # 1. Session/Character identification (immediate context)
        character_display = "the DM" if character_name == "DM" else character_name
        session_info = (
            f"This is the {ordinal(session_number)} session for {character_display}."
        )

        # 2. Session-specific context (current session details)
        session_context = f" {session_notes}" if session_notes else ""

        # 3. Current chunk context (processing-specific info)
        chunk_context = f" This is {chunk_info}." if chunk_info else ""

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
            f"{session_info}{session_context}{chunk_context}"
            f"{campaign_context}"
            f"{transcript_context}"
            f"{recent_chunks_context}"
        )

        return full_prompt

    def _call_whisper_api(
        self,
        file_path: Path,
        character_name: str,
        session_number: int,
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
                        session_number,
                        chunk_info,
                        previous_chunks_text,
                        previous_transcript,
                        session_notes,
                    ),
                    temperature=0,
                    language="en",
                )

                # Validate response structure using WhisperResponse
                whisper_response = WhisperResponse(response)
                if not whisper_response.is_valid:
                    print(
                        f"⚠️ Invalid response format from Whisper API for {file_path.name}"
                    )
                    return None

                return whisper_response

        except Exception as e:
            print(f"❌ Failed to transcribe {file_path.name}: {e}")
            return None

    def _process_chunks(
        self,
        chunk_paths: List[Path],
        character_name: str,
        session_number: int,
        previous_transcript: str,
        session_notes: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Process multiple audio chunks and return combined transcript data. Pure function - no file I/O."""
        all_transcripts = []
        previous_chunks_text = ""

        for i, chunk_path in enumerate(chunk_paths):
            chunk_info = f"chunk {i+1} of {len(chunk_paths)}"

            whisper_response = self._call_whisper_api(
                chunk_path,
                character_name,
                session_number,
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
