from django.core.management.base import BaseCommand
from tqdm import tqdm
from nucleus.ai_helpers import openai_summarize_text_chat
from nucleus.models import GameLog
from nucleus.gdrive import fetch_airel_file_text
import json


class Command(BaseCommand):
    help = (
        "Create up to 3 AI suggestion objects for each log, if they don't already exist"
    )

    def handle(self, *args, **options):
        logs = GameLog.objects.all()
        for log in tqdm(logs):
            num_suggestions = log.ailogsuggestion_set.count()
            if num_suggestions >= 3:
                continue
            log_text = fetch_airel_file_text(log.google_id)
            for i in range(3 - num_suggestions):
                try:
                    response = openai_summarize_text_chat(log_text)
                    res_json = response["choices"][0]["message"]["content"]
                    obj = json.loads(res_json)
                    suggestion = log.ailogsuggestion_set.create(
                        title=obj["title"],
                        brief=obj["brief"],
                        associations=obj["associations"],
                        characters=obj["characters"],
                        items=obj["items"],
                        places=obj["places"],
                        races=obj["races"],
                    )
                    print("Created AI suggestion with id", suggestion.id)
                except Exception as e:
                    try:
                        response = openai_summarize_text_chat(log.summary)
                        res_json = response["choices"][0]["message"]["content"]
                        obj = json.loads(res_json)
                        suggestion = log.ailogsuggestion_set.create(
                            title=obj["title"],
                            brief=obj["brief"],
                            associations=obj["associations"],
                            characters=obj["characters"],
                            items=obj["items"],
                            places=obj["places"],
                            races=obj["races"],
                        )
                        print(
                            "Created AI suggestion from summary with id", suggestion.id
                        )
                    except Exception as e:
                        print(
                            f"Error creating AI suggestion from summary for {log}: {e}"
                        )
                    print(f"Error creating AI suggestion for {log}: {e}")
                    continue
