"""
Django management command to test Celery setup.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from transcription.tasks import health_check_task


class Command(BaseCommand):
    help = 'Test Celery setup and task execution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run task asynchronously (requires Celery worker)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing Celery setup...')
        )

        if options['async']:
            self.stdout.write('Submitting async task...')
            try:
                result = health_check_task.delay()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Task submitted successfully. Task ID: {result.id}'
                    )
                )
                self.stdout.write(
                    'Check Celery worker logs to see task execution.'
                )
                
                # Optionally wait for result (with timeout)
                try:
                    task_result = result.get(timeout=10)
                    self.stdout.write(
                        self.style.SUCCESS(f'Task result: {task_result}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Could not get task result (worker might not be running): {e}'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to submit task: {e}')
                )
        else:
            self.stdout.write('Running task synchronously...')
            try:
                result = health_check_task()
                self.stdout.write(
                    self.style.SUCCESS(f'Task result: {result}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Task failed: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS('Celery test completed!')
        )