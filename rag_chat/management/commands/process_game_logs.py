from django.core.management.base import BaseCommand
from rag_chat.tasks import process_game_log, process_all_game_logs
from nucleus.models import GameLog


class Command(BaseCommand):
    help = "Process game logs for RAG search"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all game logs",
        )
        parser.add_argument(
            "--id",
            type=int,
            help="Process a specific game log by ID",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reprocessing even if already processed",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of logs to process (for testing)",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run synchronously instead of using Celery (for testing)",
        )

    def handle(self, *args, **options):
        if options["id"]:
            # Process single game log
            game_log_id = options["id"]
            self.stdout.write(f"Processing game log ID: {game_log_id}")

            try:
                game_log = GameLog.objects.get(id=game_log_id)
                self.stdout.write(f"Found game log: {game_log.title}")

                from rag_chat.tasks import process_game_log

                if options["sync"]:
                    # Run synchronously for testing

                    result = process_game_log(game_log_id, options["force"])
                else:
                    # Queue with Celery
                    task = process_game_log.delay(game_log_id, options["force"])
                    result = {"task_id": task.id, "status": "queued"}

                self.stdout.write(self.style.SUCCESS(f"Result: {result}"))

            except GameLog.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Game log with ID {game_log_id} not found")
                )

        elif options["all"]:
            # Process all game logs
            self.stdout.write("Processing all game logs...")

            if options["sync"]:
                # For sync mode, get the logs and process them one by one
                queryset = GameLog.objects.all().order_by("game_date")
                if not options["force"]:
                    queryset = queryset.filter(chunks__isnull=True).distinct()
                if options["limit"]:
                    queryset = queryset[: options["limit"]]

                total = queryset.count()
                self.stdout.write(f"Found {total} logs to process")

                for i, game_log in enumerate(queryset, 1):
                    self.stdout.write(f"Processing {i}/{total}: {game_log.title}")
                    result = process_game_log(game_log.id, options["force"])
                    self.stdout.write(f"  Result: {result['status']}")

            else:
                # Queue with Celery
                task = process_all_game_logs.delay(options["force"], options["limit"])
                self.stdout.write(
                    self.style.SUCCESS(f"Queued batch processing task: {task.id}")
                )

        else:
            self.stdout.write(
                self.style.ERROR("Please specify --all or --id <game_log_id>")
            )
