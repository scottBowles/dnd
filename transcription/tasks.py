"""
Celery tasks for transcription processing.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from .services import TranscriptionService, TranscriptionConfig
from .models import AudioTranscript
from nucleus.models import SessionAudio

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_session_audio_task(
    self, session_audio_id, previous_transcript="", session_notes=""
):
    print("process_session_audio_task called with session_audio_id =", session_audio_id)
    """
    Process a SessionAudio instance asynchronously.
    
    Args:
        session_audio_id: ID of the SessionAudio instance to process
        previous_transcript: Previous transcript text for context
        session_notes: Session notes for context
        
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    try:
        logger.info(
            f"Starting transcription task for SessionAudio ID: {session_audio_id}"
        )

        # Get the SessionAudio instance
        try:
            session_audio = SessionAudio.objects.get(id=session_audio_id)
        except ObjectDoesNotExist:
            logger.error(f"SessionAudio with ID {session_audio_id} not found")
            return False

        # Create transcription service
        service = TranscriptionService()

        # Process the audio
        result = service.process_session_audio(
            session_audio=session_audio,
            previous_transcript=previous_transcript,
            session_notes=session_notes,
        )

        if result:
            logger.info(f"Successfully processed SessionAudio ID: {session_audio_id}")
        else:
            logger.warning(f"Failed to process SessionAudio ID: {session_audio_id}")

        return result

    except Exception as exc:
        logger.error(f"Error processing SessionAudio ID {session_audio_id}: {str(exc)}")

        # Only retry for certain types of exceptions (network errors, temporary failures)
        # Don't retry for validation errors or business logic failures
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,  # Can include network issues
        )

        # Also check for specific API error patterns that might be retryable
        is_retryable = (
            isinstance(exc, retryable_exceptions)
            or "timeout" in str(exc).lower()
            or "connection" in str(exc).lower()
            or "temporary" in str(exc).lower()
            or "rate limit" in str(exc).lower()
        )

        if is_retryable and self.request.retries < self.max_retries:
            logger.info(
                f"Retrying task for SessionAudio ID {session_audio_id} (attempt {self.request.retries + 1}) due to retryable error: {type(exc).__name__}"
            )
            raise self.retry(exc=exc)
        else:
            if not is_retryable:
                logger.error(
                    f"Non-retryable error for SessionAudio ID {session_audio_id}: {type(exc).__name__}"
                )
            else:
                logger.error(
                    f"Max retries exceeded for SessionAudio ID {session_audio_id}"
                )
            return False


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_session_log_task(self, gamelog_id, method="concat", model="gpt-4o"):
    """
    Generate a session log asynchronously.

    Args:
        gamelog_id: ID of the GameLog instance
        method: Method to use for log generation ('concat' or 'segment')
        model: OpenAI model to use

    Returns:
        str: Generated session log or None if failed
    """
    try:
        logger.info(f"Starting session log generation for GameLog ID: {gamelog_id}")

        # Import here to avoid circular imports
        from nucleus.models import GameLog
        from .services import TranscriptionService

        try:
            gamelog = GameLog.objects.get(id=gamelog_id)
        except ObjectDoesNotExist:
            logger.error(f"GameLog with ID {gamelog_id} not found")
            return None

        # Generate the session log using the static method
        result = TranscriptionService.generate_session_log_from_transcripts(
            gamelog=gamelog, model=model, method=method
        )

        logger.info(f"Successfully generated session log for GameLog ID: {gamelog_id}")
        return result

    except Exception as exc:
        logger.error(
            f"Error generating session log for GameLog ID {gamelog_id}: {str(exc)}"
        )

        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying session log task for GameLog ID {gamelog_id} (attempt {self.request.retries + 1})"
            )
            raise self.retry(exc=exc)
        else:
            logger.error(
                f"Max retries exceeded for session log generation for GameLog ID {gamelog_id}"
            )
            return None


@shared_task
def cleanup_old_audio_files_task():
    """
    Cleanup old audio files and temporary files.

    This task can be scheduled to run periodically to clean up
    temporary audio chunks and old processed files.
    """
    try:
        logger.info("Starting cleanup of old audio files")

        # Import here to avoid circular imports
        from .utils import cleanup_temporary_files

        cleanup_temporary_files()

        logger.info("Successfully completed audio files cleanup")
        return True

    except Exception as exc:
        logger.error(f"Error during audio files cleanup: {str(exc)}")
        return False
