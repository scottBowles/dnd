from celery import shared_task
from django.db import transaction
from .models import GameLogChunk
from .embeddings import get_embedding, chunk_document, build_chunk_metadata
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_game_log(self, game_log_id: int, force_reprocess: bool = False):
    """
    Process a game log into chunks with embeddings for RAG search

    Args:
        game_log_id: ID of the GameLog to process
        force_reprocess: If True, delete existing chunks and reprocess
    """
    from nucleus.models import GameLog  # Import here to avoid circular imports

    try:
        game_log = GameLog.objects.get(id=game_log_id)
        logger.info(f"Processing game log: {game_log.title} (ID: {game_log_id})")

        # Check if already processed (unless forcing reprocess)
        if not force_reprocess and game_log.chunks.exists():
            logger.info(f"Game log {game_log_id} already processed. Skipping.")
            return {
                "status": "skipped",
                "game_log_id": game_log_id,
                "message": "Already processed",
            }

        # If forcing reprocess, delete existing chunks
        if force_reprocess:
            deleted_count = game_log.chunks.count()
            game_log.chunks.all().delete()
            logger.info(f"Deleted {deleted_count} existing chunks for reprocessing")

        # Get the text content
        try:
            text_content = game_log.log_text
            if not text_content or not text_content.strip():
                logger.warning(f"No text content found for game log {game_log_id}")
                return {
                    "status": "error",
                    "game_log_id": game_log_id,
                    "message": "No text content available",
                }
        except Exception as e:
            logger.error(f"Failed to fetch text for game log {game_log_id}: {str(e)}")
            return {
                "status": "error",
                "game_log_id": game_log_id,
                "message": f"Failed to fetch text: {str(e)}",
            }

        # Split into chunks
        chunks = chunk_document(text_content)
        if not chunks:
            logger.warning(f"No chunks created for game log {game_log_id}")
            return {
                "status": "error",
                "game_log_id": game_log_id,
                "message": "No chunks created from text",
            }

        logger.info(f"Created {len(chunks)} chunks for game log {game_log_id}")

        # Process each chunk
        created_chunks = []
        total_chunks = len(chunks)

        for i, chunk_text in enumerate(chunks):
            try:
                # Get embedding
                embedding = get_embedding(chunk_text)

                # Build metadata
                metadata = build_chunk_metadata(game_log, chunk_text, i, total_chunks)

                # Create the chunk record
                with transaction.atomic():
                    chunk_obj = GameLogChunk.objects.create(
                        game_log=game_log,
                        chunk_text=chunk_text,
                        chunk_index=i,
                        embedding=embedding,
                        metadata=metadata,
                    )
                    created_chunks.append(chunk_obj.id)

                logger.info(
                    f"Created chunk {i+1}/{total_chunks} for game log {game_log_id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process chunk {i} for game log {game_log_id}: {str(e)}"
                )
                # Continue with other chunks rather than failing completely
                continue

        logger.info(
            f"Successfully processed game log {game_log_id}: {len(created_chunks)} chunks created"
        )

        return {
            "status": "success",
            "game_log_id": game_log_id,
            "chunks_created": len(created_chunks),
            "chunk_ids": created_chunks,
            "title": game_log.title,
        }

    except GameLog.DoesNotExist:
        error_msg = f"GameLog with ID {game_log_id} does not exist"
        logger.error(error_msg)
        return {"status": "error", "game_log_id": game_log_id, "message": error_msg}

    except Exception as e:
        logger.error(f"Unexpected error processing game log {game_log_id}: {str(e)}")

        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying game log {game_log_id} (attempt {self.request.retries + 1})"
            )
            raise self.retry(
                countdown=60 * (2**self.request.retries)
            )  # Exponential backoff

        return {"status": "error", "game_log_id": game_log_id, "message": str(e)}


@shared_task
def process_all_game_logs(force_reprocess: bool = False, limit: int = None):
    """
    Process all game logs in the database

    Args:
        force_reprocess: If True, reprocess even already processed logs
        limit: Optional limit on number of logs to process (for testing)
    """
    from nucleus.models import GameLog

    logger.info(
        f"Starting batch processing of all game logs (force_reprocess={force_reprocess})"
    )

    # Get logs to process
    queryset = GameLog.objects.all().order_by("game_date")

    if not force_reprocess:
        # Only process logs that haven't been processed yet
        queryset = queryset.filter(chunks__isnull=True).distinct()

    if limit:
        queryset = queryset[:limit]

    total_logs = queryset.count()
    logger.info(f"Found {total_logs} game logs to process")

    if total_logs == 0:
        return {"status": "completed", "total_logs": 0, "message": "No logs to process"}

    # Queue individual tasks
    task_results = []
    for game_log in queryset:
        try:
            task = process_game_log.delay(game_log.id, force_reprocess)
            task_results.append(
                {
                    "game_log_id": game_log.id,
                    "task_id": task.id,
                    "title": game_log.title,
                }
            )
            logger.info(
                f"Queued processing task for game log {game_log.id}: {game_log.title}"
            )
        except Exception as e:
            logger.error(f"Failed to queue task for game log {game_log.id}: {str(e)}")

    return {
        "status": "queued",
        "total_logs": total_logs,
        "tasks_queued": len(task_results),
        "task_results": task_results,
    }


@shared_task
def cleanup_orphaned_chunks():
    """
    Clean up chunks that reference deleted game logs
    """
    from nucleus.models import GameLog

    # Find chunks whose game logs no longer exist
    orphaned_chunks = GameLogChunk.objects.exclude(
        game_log_id__in=GameLog.objects.values_list("id", flat=True)
    )

    count = orphaned_chunks.count()
    if count > 0:
        orphaned_chunks.delete()
        logger.info(f"Cleaned up {count} orphaned chunks")

    return {"status": "completed", "orphaned_chunks_deleted": count}
