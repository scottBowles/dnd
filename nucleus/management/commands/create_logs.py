from django.core.management.base import BaseCommand
from tqdm import tqdm
from nucleus.models import GameLog
from nucleus.gdrive import fetch_all_airel_logs


class Command(BaseCommand):
    help = "Create GameLog objects from google drive and update existing ones"

    def handle(self, *args, **options):
        log_files = fetch_all_airel_logs()
        for log_file in tqdm(log_files):
            log, created = GameLog.objects.get_or_create(url=log_file["webViewLink"])
            if not created:
                log.update_from_google_file_info(log_file)
                log.save()
