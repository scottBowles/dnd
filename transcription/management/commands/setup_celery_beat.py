"""
Django management command to setup Celery Beat database tables.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Set up Celery Beat database tables'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Celery Beat database tables...')
        
        try:
            # Run migrations for django_celery_beat
            call_command('migrate', 'django_celery_beat', verbosity=1)
            
            self.stdout.write(
                self.style.SUCCESS('Celery Beat tables created successfully!')
            )
            
            self.stdout.write(
                'You can now use Celery Beat for scheduled tasks.'
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to set up Celery Beat tables: {e}')
            )