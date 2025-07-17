import tempfile
import time
from pathlib import Path
from typing import List, Optional, TypedDict
from .AudioProcessingService import AudioData


class TranscriptChunkDict(TypedDict):
    transcript: dict  # Raw Whisper response (verbose_json)
    chunk: AudioData  # AudioData object


class CombinedTranscriptDict(TypedDict, total=False):
    text: str
    segments: List[dict]
    chunks: List[dict]  # List of raw Whisper responses


import openai
from pydub import AudioSegment

from nucleus.models import GameLog, SessionAudio
from transcription.models import AudioTranscript

from ..models import AudioTranscript, TranscriptChunk
from ..responses import WhisperResponse
from ..tasks import generate_session_log_task, process_session_audio_task
from ..utils import ordinal
from .CampaignContextService import CampaignContextService
from .TranscriptCleaner import TranscriptCleaner
from .TranscriptionConfig import TranscriptionConfig
from .AudioProcessingService import AudioProcessingService


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

        start_time = time.time()
        time_offset_mapping = None

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

        # Preprocess audio if enabled
        if self.config.enable_audio_preprocessing:
            try:
                audio = AudioSegment.from_file(temp_path)
                audio = self.audio_service.normalize_audio(audio)
                # Overwrite temp_path with normalized audio
                audio.export(temp_path, format=temp_path.suffix[1:])
            except Exception as e:
                print(f"⚠️ Could not apply preprocessing for timing: {e}")

        # Split file
        audio_chunks = self.audio_service.split_audio_file(
            temp_path, Path(file_name).stem
        )

        success = False
        try:
            # If only one chunk, process directly
            if len(audio_chunks) == 1:
                chunk = audio_chunks[0]
                whisper_response = self._call_whisper_api(
                    file_path=chunk.file_path,
                    character_name=Path(file_name).stem,
                    chunk_info="",
                    previous_chunks_text="",
                    previous_transcript=previous_transcript,
                    session_notes=session_notes,
                )

                if whisper_response:
                    # Convert segment times to original timeline using AudioData method
                    if hasattr(whisper_response, "segments"):
                        for segment in whisper_response.segments:
                            segment["start"] = (
                                chunk.convert_processed_to_original_timestamp(
                                    segment["start"]
                                )
                            )
                            segment["end"] = (
                                chunk.convert_processed_to_original_timestamp(
                                    segment["end"]
                                )
                            )
                    processing_time = time.time() - start_time
                    self._save_audio_transcript(
                        session_audio=session_audio,
                        file_path=chunk.file_path,
                        character_name=Path(file_name).stem,
                        file_size_mb=file_size_mb,
                        whisper_response=whisper_response,
                        was_split=False,
                        num_chunks=1,
                        processing_time=processing_time,
                    )
                    success = True
            else:
                combined_transcript: Optional[CombinedTranscriptDict] = None
                all_transcripts: List[TranscriptChunkDict] = []
                previous_chunks_text = ""

                for i, chunk in enumerate(audio_chunks):
                    chunk_info = f"the {ordinal(i+1)} chunk of {len(audio_chunks)}"

                    whisper_response = self._call_whisper_api(
                        file_path=chunk.file_path,
                        character_name=Path(file_name).stem,
                        chunk_info=chunk_info,
                        previous_chunks_text=previous_chunks_text,
                        previous_transcript=previous_transcript,
                        session_notes=session_notes,
                    )

                    if whisper_response:
                        # Convert segment times to original timeline for this chunk using AudioData method
                        if hasattr(whisper_response, "segments"):
                            for segment in whisper_response.segments:
                                segment["start"] = (
                                    chunk.convert_processed_to_original_timestamp(
                                        segment["start"]
                                    )
                                )
                                segment["end"] = (
                                    chunk.convert_processed_to_original_timestamp(
                                        segment["end"]
                                    )
                                )
                        # Collect transcripts for processing
                        all_transcripts.append(
                            {
                                "transcript": whisper_response.raw_response,
                                "chunk": chunk,
                            }
                        )

                        # Update previous chunks text for subsequent chunk prompts
                        chunk_text = whisper_response.text
                        if chunk_text:
                            previous_chunks_text += f"\n\n{chunk_text}"

                        # Delay between requests
                        if i < len(audio_chunks) - 1:
                            time.sleep(self.config.delay_between_requests)

                if all_transcripts:
                    combined_transcript = self._create_combined_transcript(
                        [item["transcript"] for item in all_transcripts]
                    )

                if combined_transcript:
                    processing_time = time.time() - start_time
                    audio_transcript = self._save_audio_transcript(
                        session_audio=session_audio,
                        file_path=temp_path,
                        character_name=Path(file_name).stem,
                        file_size_mb=file_size_mb,
                        whisper_response=combined_transcript,
                        was_split=True,
                        num_chunks=len(audio_chunks),
                        processing_time=processing_time,
                    )
                    self._save_transcript_chunks(
                        audio_transcript,
                        combined_transcript,
                        [item["chunk"].file_path for item in all_transcripts],
                    )
                    success = True
        finally:
            # Explicitly clean up all chunk temp files
            from .AudioProcessingService import cleanup_audio_data_files

            cleanup_audio_data_files(audio_chunks)
            # Explicitly clean up the uploaded temp file
            try:
                temp_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"Warning: failed to delete temp file {temp_path}: {e}")
        return success

    # ========================================
    # Private Implementation Methods
    # ========================================

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
    ) -> AudioTranscript:
        """Save audio transcript data to database."""

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
        combined_transcript: CombinedTranscriptDict,
        chunk_paths: List[Path],
    ):
        """Save individual chunk data to database."""
        chunk_transcripts = combined_transcript.get("chunks", [])

        for i, (chunk_path, chunk_transcript) in enumerate(
            zip(chunk_paths, chunk_transcripts)
        ):
            # Extract chunk data - chunk_transcript is already the raw transcript data
            whisper_response = WhisperResponse(chunk_transcript)
            chunk_text = whisper_response.text

            # Set chunk timing offset based on chunk index and config
            start_time_offset = i * self.config.chunk_duration_minutes * 60

            # Get duration from segments if available
            duration_seconds = 0.0
            if whisper_response.segments:
                last_segment = max(
                    whisper_response.segments, key=lambda s: s.get("end", 0)
                )
                duration_seconds = last_segment.get("end", 0.0)

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

        # 3. Campaign context (broader world knowledge)
        formatted_context = self.context_service.get_formatted_context(max_length=800)
        campaign_context = (
            f"\n\nCampaign Context: {formatted_context}" if formatted_context else ""
        )

        # 4. Previous transcript context (historical session data)
        transcript_context = (
            f"\n\nPrevious Transcript:\n{previous_transcript}"
            if previous_transcript
            else ""
        )

        # 5. Recent chunks context (immediate previous processing context)
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
                    f.seek(0)  # Rewind file pointer before retry
                    try:
                        # Retry without prompt to reduce hallucinations
                        response = openai.Audio.transcribe(
                            model="whisper-1",
                            file=f,
                            response_format="verbose_json",
                            temperature=0,
                            language="en",
                        )
                        whisper_response = WhisperResponse(response)
                    except Exception as retry_exc:
                        print(
                            f"⚠️ Retry failed for {file_path.name}: {retry_exc}. Using first attempt's transcript."
                        )
                        # Return the original whisper_response from the first attempt
                        return whisper_response

                return whisper_response

        except Exception as e:
            print(f"❌ Failed to transcribe {file_path.name}: {e}")
            return None

    def _create_combined_transcript(
        self, all_transcripts: List[dict]
    ) -> Optional[CombinedTranscriptDict]:
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
            combined_transcript: CombinedTranscriptDict = {
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
        return ""

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

                return process_session_audio_task.delay_on_commit(
                    session_audio.pk, previous_transcript, session_notes
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
