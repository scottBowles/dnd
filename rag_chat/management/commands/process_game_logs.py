# rag_chat/management/commands/process_content.py
from django.core.management.base import BaseCommand
from django.apps import apps
from rag_chat.tasks import (
    process_content,
    process_all_content,
    process_custom_content,
    # migrate_legacy_chunks,
    cleanup_orphaned_chunks,
)
from rag_chat.content_processors import CONTENT_PROCESSORS
from rag_chat.models import ContentChunk
import json


class Command(BaseCommand):
    help = "Process various content types for RAG search"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=list(CONTENT_PROCESSORS.keys()),
            help="Content type to process (game_log, character, place, etc.)",
        )
        parser.add_argument(
            "--id",
            type=str,
            help="Process a specific object by ID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all content of specified type(s)",
        )
        parser.add_argument(
            "--types",
            nargs="+",
            choices=[k for k in CONTENT_PROCESSORS.keys() if k != "custom"],
            help="Multiple content types to process (excludes custom)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reprocessing even if already processed",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of objects to process (for testing)",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run synchronously instead of using Celery (for testing)",
        )
        parser.add_argument(
            "--custom",
            help="Process custom content from JSON file or string",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Clean up orphaned chunks",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show content statistics",
        )

    def handle(self, *args, **options):
        if options["stats"]:
            self.show_stats()
            return

        if options["migrate_legacy"]:
            self.handle_migration(options)
            return

        if options["cleanup"]:
            self.handle_cleanup(options)
            return

        if options["custom"]:
            self.handle_custom_content(options)
            return

        if options["id"] and options["type"]:
            self.handle_single_object(options)
        elif options["all"] or options["types"]:
            self.handle_batch_processing(options)
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Please specify one of: --id with --type, --all, --types, --custom, --cleanup, or --stats"
                )
            )

    def handle_single_object(self, options):
        """Process a single object"""
        content_type = options["type"]
        object_id = options["id"]

        self.stdout.write(f"Processing {content_type} with ID: {object_id}")

        try:
            # Verify object exists first
            obj = self.get_object(content_type, object_id)
            if not obj:
                self.stdout.write(
                    self.style.ERROR(f"{content_type} with ID {object_id} not found")
                )
                return

            self.stdout.write(
                f"Found: {getattr(obj, 'name', getattr(obj, 'title', str(obj)))}"
            )

            if options["sync"]:
                from rag_chat.tasks import process_content

                result = process_content(content_type, object_id, options["force"])
            else:
                task = process_content.delay(content_type, object_id, options["force"])
                result = {"task_id": task.id, "status": "queued"}

            self.stdout.write(self.style.SUCCESS(f"Result: {result}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def handle_batch_processing(self, options):
        """Process multiple objects"""
        if options["types"]:
            content_types = options["types"]
        elif options["type"]:
            content_types = [options["type"]]
        else:
            # Default to all main content types
            content_types = [
                "game_log",
                "character",
                "place",
                "item",
                "artifact",
                "race",
            ]

        self.stdout.write(f"Processing content types: {', '.join(content_types)}")

        if options["sync"]:
            self.handle_sync_batch(content_types, options)
        else:
            task = process_all_content.delay(
                content_types=content_types,
                force_reprocess=options["force"],
                limit=options["limit"],
            )
            self.stdout.write(
                self.style.SUCCESS(f"Queued batch processing task: {task.id}")
            )

    def handle_sync_batch(self, content_types, options):
        """Handle synchronous batch processing"""
        for content_type in content_types:
            self.stdout.write(f"\n--- Processing {content_type} ---")

            try:
                objects = self.get_objects_to_process(
                    content_type, options["force"], options["limit"]
                )
                total = len(objects)

                if total == 0:
                    self.stdout.write(f"No {content_type} objects to process")
                    continue

                self.stdout.write(f"Found {total} {content_type} objects to process")

                for i, obj in enumerate(objects, 1):
                    object_id = str(obj.id)
                    title = getattr(obj, "name", getattr(obj, "title", str(obj)))

                    self.stdout.write(f"Processing {i}/{total}: {title}")

                    from rag_chat.tasks import process_content

                    result = process_content(content_type, object_id, options["force"])

                    status_style = (
                        self.style.SUCCESS
                        if result["status"] == "success"
                        else self.style.WARNING
                    )
                    self.stdout.write(
                        f"  {status_style(result['status'])}: {result.get('message', '')}"
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {content_type}: {str(e)}")
                )

    def handle_custom_content(self, options):
        """Handle custom content processing"""
        custom_input = options["custom"]

        try:
            # Try to parse as JSON first
            if custom_input.startswith("{") or custom_input.endswith(".json"):
                if custom_input.endswith(".json"):
                    with open(custom_input, "r") as f:
                        data = json.load(f)
                else:
                    data = json.loads(custom_input)

                # Handle single object or list
                if isinstance(data, list):
                    for item in data:
                        self.process_single_custom_content(item, options)
                else:
                    self.process_single_custom_content(data, options)
            else:
                # Treat as simple text content
                data = {"title": "Custom Content", "content": custom_input}
                self.process_single_custom_content(data, options)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to process custom content: {str(e)}")
            )

    def process_single_custom_content(self, data, options):
        """Process a single custom content item"""
        required_fields = ["title", "content"]
        if not all(field in data for field in required_fields):
            self.stdout.write(
                self.style.ERROR(
                    f"Custom content must have 'title' and 'content' fields"
                )
            )
            return

        title = data["title"]
        content = data["content"]
        object_id = data.get("object_id")
        metadata = data.get("metadata", {})

        self.stdout.write(f"Processing custom content: {title}")

        if options["sync"]:
            from rag_chat.tasks import process_custom_content

            result = process_custom_content(title, content, object_id, metadata)
        else:
            task = process_custom_content.delay(title, content, object_id, metadata)
            result = {"task_id": task.id, "status": "queued"}

        self.stdout.write(self.style.SUCCESS(f"Result: {result}"))

    # def handle_migration(self, options):
    #     """Handle legacy chunk migration"""
    #     self.stdout.write("Starting migration of legacy GameLogChunk records...")

    #     if options["sync"]:
    #         from rag_chat.tasks import migrate_legacy_chunks

    #         result = migrate_legacy_chunks()
    #     else:
    #         task = migrate_legacy_chunks.delay()
    #         result = {"task_id": task.id, "status": "queued"}

    #     self.stdout.write(self.style.SUCCESS(f"Migration result: {result}"))

    def handle_cleanup(self, options):
        """Handle orphaned chunk cleanup"""
        self.stdout.write("Starting cleanup of orphaned chunks...")

        if options["sync"]:
            from rag_chat.tasks import cleanup_orphaned_chunks

            result = cleanup_orphaned_chunks()
        else:
            task = cleanup_orphaned_chunks.delay()
            result = {"task_id": task.id, "status": "queued"}

        self.stdout.write(self.style.SUCCESS(f"Cleanup result: {result}"))

    def show_stats(self):
        """Show content statistics"""
        from django.db.models import Count

        # from rag_chat.models import GameLogChunk

        self.stdout.write(self.style.SUCCESS("=== Content Statistics ===\n"))

        # New ContentChunk statistics
        chunk_stats = (
            ContentChunk.objects.values("content_type")
            .annotate(count=Count("id"))
            .order_by("content_type")
        )

        self.stdout.write("Content Chunks by Type:")
        total_chunks = 0
        for stat in chunk_stats:
            count = stat["count"]
            total_chunks += count
            self.stdout.write(f"  {stat['content_type']}: {count}")

        # Legacy chunks
        # legacy_count = GameLogChunk.objects.count()
        # if legacy_count > 0:
        #     self.stdout.write(f"  legacy_game_log: {legacy_count}")
        #     total_chunks += legacy_count

        self.stdout.write(f"\nTotal chunks: {total_chunks}")

        # Show available objects by type
        self.stdout.write("\nAvailable Objects by Type:")
        for content_type in [
            "game_log",
            "character",
            "place",
            "item",
            "artifact",
            "race",
        ]:
            try:
                objects = self.get_objects_to_process(
                    content_type, force_reprocess=True
                )
                processed_objects = self.get_processed_object_count(content_type)
                total_objects = len(objects) + processed_objects

                self.stdout.write(
                    f"  {content_type}: {total_objects} total, {processed_objects} processed"
                )
            except Exception as e:
                self.stdout.write(f"  {content_type}: Error getting count - {str(e)}")

    def get_object(self, content_type, object_id):
        """Get a single object by type and ID"""
        model_map = {
            "game_log": ("nucleus", "GameLog"),
            "character": ("character", "Character"),  # Adjust app names as needed
            "place": ("place", "Place"),
            "item": ("item", "Item"),
            "artifact": ("artifact", "Artifact"),
            "race": ("race", "Race"),
        }

        if content_type not in model_map:
            return None

        try:
            app_label, model_name = model_map[content_type]
            model = apps.get_model(app_label, model_name)
            return model.objects.get(id=object_id)
        except Exception:
            return None

    def get_objects_to_process(self, content_type, force_reprocess=False, limit=None):
        """Get objects that need processing"""
        model_map = {
            "game_log": ("nucleus", "GameLog"),
            "character": ("character", "Character"),
            "place": ("place", "Place"),
            "item": ("item", "Item"),
            "artifact": ("artifact", "Artifact"),
            "race": ("race", "Race"),
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

            # Apply ordering
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
            self.stdout.write(
                self.style.ERROR(f"Failed to get {content_type} objects: {str(e)}")
            )
            return []

    def get_processed_object_count(self, content_type):
        """Get count of already processed objects"""
        try:
            return (
                ContentChunk.objects.filter(content_type=content_type)
                .values("object_id")
                .distinct()
                .count()
            )
        except Exception:
            return 0
