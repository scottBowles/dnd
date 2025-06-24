"""
Celery tasks for transcription processing.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from .services import TranscriptionService, TranscriptionConfig
from .models import SessionAudio, AudioTranscript

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_session_audio_task(self, session_audio_id, previous_transcript="", session_notes=""):
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
        logger.info(f"Starting transcription task for SessionAudio ID: {session_audio_id}")
        
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
            session_notes=session_notes
        )
        
        if result:
            logger.info(f"Successfully processed SessionAudio ID: {session_audio_id}")
        else:
            logger.warning(f"Failed to process SessionAudio ID: {session_audio_id}")
            
        return result
        
    except Exception as exc:
        logger.error(f"Error processing SessionAudio ID {session_audio_id}: {str(exc)}")
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for SessionAudio ID {session_audio_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        else:
            logger.error(f"Max retries exceeded for SessionAudio ID {session_audio_id}")
            return False


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_session_log_task(self, gamelog_id, method="concat", previous_transcript="", session_notes=""):
    """
    Generate a session log asynchronously.
    
    Args:
        gamelog_id: ID of the GameLog instance
        method: Method to use for log generation ('concat' or 'segment')
        previous_transcript: Previous transcript for context
        session_notes: Session notes for context
        
    Returns:
        dict: Generated session log data or None if failed
    """
    try:
        logger.info(f"Starting session log generation for GameLog ID: {gamelog_id}")
        
        # Import here to avoid circular imports
        from nucleus.models import GameLog
        
        try:
            gamelog = GameLog.objects.get(id=gamelog_id)
        except ObjectDoesNotExist:
            logger.error(f"GameLog with ID {gamelog_id} not found")
            return None
            
        # Get all audio transcripts for this game log
        audio_transcripts = AudioTranscript.objects.filter(
            session_audio__gamelog=gamelog
        ).order_by('created_at')
        
        if not audio_transcripts.exists():
            logger.warning(f"No audio transcripts found for GameLog ID: {gamelog_id}")
            return None
            
        # Create transcription service
        service = TranscriptionService()
        
        # Generate the session log
        result = service.generate_session_log(
            audio_transcripts=list(audio_transcripts),
            method=method,
            previous_transcript=previous_transcript,
            session_notes=session_notes
        )
        
        logger.info(f"Successfully generated session log for GameLog ID: {gamelog_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Error generating session log for GameLog ID {gamelog_id}: {str(exc)}")
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying session log task for GameLog ID {gamelog_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        else:
            logger.error(f"Max retries exceeded for session log generation for GameLog ID {gamelog_id}")
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


@shared_task
def health_check_task():
    """
    Simple health check task to verify Celery is working.
    """
    logger.info("Celery health check task executed successfully")
    return "Celery is working!"