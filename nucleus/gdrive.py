from django.conf import settings
from googleapiclient.discovery import build

GOOGLE_API_KEY = settings.GOOGLE_API_KEY
AIREL_FOLDER_ID = settings.AIREL_FOLDER_ID


def fetch_airel_folder():
    with build("drive", "v3", developerKey=GOOGLE_API_KEY) as service:
        results = (
            service.files()
            .list(
                q=f"'{AIREL_FOLDER_ID}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, webViewLink, createdTime)",
            )
            .execute()
        )
        return results


def fetch_airel_file(id):
    with build("drive", "v3", developerKey=GOOGLE_API_KEY) as service:
        results = (
            service.files().get(fileId=id, fields="id, name, webViewLink, createdTime")
            # .get(fileId=id, fields="*") # use this to see all available fields
            .execute()
        )
        return results


def fetch_airel_file_text(id):
    """
    Fetches the text of a file from google drive
    """
    with build("drive", "v3", developerKey=GOOGLE_API_KEY) as service:
        results = service.files().export(fileId=id, mimeType="text/plain").execute()
        return results.decode("utf-8")
