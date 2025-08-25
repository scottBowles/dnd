# rag_chat/tasks.py
from celery import shared_task
from django.db import transaction
from django.apps import apps
from .models import ContentChunk

# from .models import ContentChunk, GameLogChunk
from .embeddings import get_embedding
from .content_processors import get_processor, CONTENT_PROCESSORS
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_content(
    self, content_type: str, object_id: str, force_reprocess: bool = False
):
    """
    Process any content type into chunks with embeddings for RAG search

    Args:
        content_type: Type of content (gamelog, character, place, etc.)
        object_id: ID of the object to process
        force_reprocess: If True, delete existing chunks and reprocess
    """
    try:
        # Get the appropriate model and processor
        obj = get_content_object(content_type, object_id)
        if not obj:
            return {
                "status": "error",
                "content_type": content_type,
                "object_id": object_id,
                "message": f"Object not found: {content_type} with ID {object_id}",
            }

        processor = get_processor(content_type)

        logger.info(
            f"Processing {content_type}: {getattr(obj, 'name', getattr(obj, 'title', object_id))}"
        )

        # Check if already processed (unless forcing reprocess)
        existing_chunks = ContentChunk.objects.filter(
            content_type=content_type, object_id=object_id
        )

        if not force_reprocess and existing_chunks.exists():
            logger.info(f"{content_type} {object_id} already processed. Skipping.")
            return {
                "status": "skipped",
                "content_type": content_type,
                "object_id": object_id,
                "message": "Already processed",
            }

        # If forcing reprocess, delete existing chunks
        if force_reprocess:
            deleted_count = existing_chunks.count()
            existing_chunks.delete()
            logger.info(f"Deleted {deleted_count} existing chunks for reprocessing")

        # Process the content
        try:
            chunk_data = processor.process_content(obj)
            if not chunk_data:
                logger.warning(f"No content generated for {content_type} {object_id}")
                return {
                    "status": "error",
                    "content_type": content_type,
                    "object_id": object_id,
                    "message": "No content could be extracted",
                }
        except Exception as e:
            logger.error(
                f"Failed to process content for {content_type} {object_id}: {str(e)}"
            )
            return {
                "status": "error",
                "content_type": content_type,
                "object_id": object_id,
                "message": f"Content processing failed: {str(e)}",
            }

        # Create chunks with embeddings
        created_chunks = []
        total_chunks = len(chunk_data)

        for i, (chunk_text, metadata) in enumerate(chunk_data):
            try:
                # Get embedding
                embedding = get_embedding(chunk_text)

                # Create the chunk record
                with transaction.atomic():
                    chunk_obj = ContentChunk.objects.create(
                        content_type=content_type,
                        object_id=object_id,
                        chunk_text=chunk_text,
                        chunk_index=i,
                        embedding=embedding,
                        metadata=metadata,
                    )
                    created_chunks.append(chunk_obj.id)

                logger.info(
                    f"Created chunk {i+1}/{total_chunks} for {content_type} {object_id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to create chunk {i} for {content_type} {object_id}: {str(e)}"
                )
                continue

        logger.info(
            f"Successfully processed {content_type} {object_id}: {len(created_chunks)} chunks created"
        )

        return {
            "status": "success",
            "content_type": content_type,
            "object_id": object_id,
            "chunks_created": len(created_chunks),
            "chunk_ids": created_chunks,
            "title": getattr(obj, "name", getattr(obj, "title", str(obj))),
        }

    except Exception as e:
        logger.error(
            f"Unexpected error processing {content_type} {object_id}: {str(e)}"
        )

        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying {content_type} {object_id} (attempt {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (2**self.request.retries))

        return {
            "status": "error",
            "content_type": content_type,
            "object_id": object_id,
            "message": str(e),
        }


@shared_task
def process_all_content(
    content_types: list = None, force_reprocess: bool = False, limit: int = None
):
    """
    Process all content of specified types

    Args:
        content_types: List of content types to process (None = all except custom)
        force_reprocess: If True, reprocess even already processed content
        limit: Optional limit on number of objects to process per type
    """
    if content_types is None:
        content_types = [
            "gamelog",
            "character",
            "place",
            "item",
            "artifact",
            "race",
            "association",
        ]

    logger.info(f"Starting batch processing of content types: {content_types}")

    total_tasks = 0
    task_results = []

    for content_type in content_types:
        try:
            # Get objects to process
            objects = get_content_objects(content_type, force_reprocess, limit)

            if not objects:
                logger.info(f"No {content_type} objects found to process")
                continue

            logger.info(f"Found {len(objects)} {content_type} objects to process")

            # Queue tasks for each object
            for obj in objects:
                try:
                    object_id = str(obj.id)
                    task = process_content.delay(
                        content_type, object_id, force_reprocess
                    )
                    task_results.append(
                        {
                            "content_type": content_type,
                            "object_id": object_id,
                            "task_id": task.id,
                            "title": getattr(
                                obj, "name", getattr(obj, "title", str(obj))
                            ),
                        }
                    )
                    total_tasks += 1

                except Exception as e:
                    logger.error(
                        f"Failed to queue task for {content_type} {obj.id}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"Failed to process content type {content_type}: {str(e)}")

    return {
        "status": "queued",
        "content_types": content_types,
        "total_tasks": total_tasks,
        "task_results": task_results,
    }


@shared_task
def cleanup_orphaned_chunks():
    """
    Clean up chunks that reference deleted objects
    """
    orphaned_count = 0

    for content_type in CONTENT_PROCESSORS.keys():
        if content_type == "custom":
            continue  # Custom content doesn't have backing objects

        try:
            # Get all chunk object_ids for this content type
            chunk_object_ids = set(
                ContentChunk.objects.filter(content_type=content_type).values_list(
                    "object_id", flat=True
                )
            )

            if not chunk_object_ids:
                continue

            # Get valid object IDs from the actual model
            valid_object_ids = set(str(id) for id in get_valid_object_ids(content_type))

            # Find orphaned chunks
            orphaned_object_ids = chunk_object_ids - valid_object_ids

            if orphaned_object_ids:
                deleted = ContentChunk.objects.filter(
                    content_type=content_type, object_id__in=orphaned_object_ids
                ).delete()

                count = deleted[0] if deleted else 0
                orphaned_count += count
                logger.info(f"Cleaned up {count} orphaned {content_type} chunks")

        except Exception as e:
            logger.error(f"Failed to cleanup {content_type} chunks: {str(e)}")

    return {
        "status": "completed",
        "orphaned_chunks_deleted": orphaned_count,
    }


# Helper functions


def get_content_object(content_type: str, object_id: str):
    """Get a content object by type and ID"""
    model_map = {
        "gamelog": ("nucleus", "GameLog"),
        "character": ("character", "Character"),  # Adjust app names as needed
        "place": ("place", "Place"),
        "item": ("item", "Item"),
        "artifact": ("item", "Artifact"),
        "race": ("race", "Race"),
        "association": ("association", "Association"),
    }

    if content_type not in model_map:
        return None

    try:
        app_label, model_name = model_map[content_type]
        model = apps.get_model(app_label, model_name)
        return model.objects.get(pk=object_id)
    except Exception:
        return None


def get_content_objects(
    content_type: str, force_reprocess: bool = False, limit: int = None
):
    """Get objects to process for a given content type"""
    model_map = {
        "gamelog": ("nucleus", "GameLog"),
        "character": ("character", "Character"),
        "place": ("place", "Place"),
        "item": ("item", "Item"),
        "artifact": ("item", "Artifact"),
        "race": ("race", "Race"),
        "association": ("association", "Association"),
    }

    if content_type not in model_map:
        return []

    try:
        app_label, model_name = model_map[content_type]
        model = apps.get_model(app_label, model_name)

        queryset = model.objects.all()

        # Filter out already processed objects unless forcing reprocess
        if not force_reprocess:
            processed_ids = (
                ContentChunk.objects.filter(content_type=content_type)
                .values_list("object_id", flat=True)
                .distinct()
            )

            processed_ids = [int(id) for id in processed_ids if id.isdigit()]
            queryset = queryset.exclude(id__in=processed_ids)

        # Apply ordering (customize as needed per model)
        if hasattr(model, "game_date"):
            queryset = queryset.order_by("game_date")
        elif hasattr(model, "name"):
            queryset = queryset.order_by("name")
        elif hasattr(model, "title"):
            queryset = queryset.order_by("title")

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    except Exception as e:
        logger.error(f"Failed to get {content_type} objects: {str(e)}")
        return []


def get_valid_object_ids(content_type: str):
    """Get valid object IDs for a content type"""
    model_map = {
        "gamelog": ("nucleus", "GameLog"),
        "character": ("character", "Character"),
        "place": ("place", "Place"),
        "item": ("item", "Item"),
        "artifact": ("item", "Artifact"),
        "race": ("race", "Race"),
        "association": ("association", "Association"),
    }

    if content_type not in model_map:
        return []

    try:
        app_label, model_name = model_map[content_type]
        model = apps.get_model(app_label, model_name)
        return model.objects.values_list("id", flat=True)
    except Exception:
        return []
