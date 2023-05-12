from django.conf import settings
from googleapiclient.discovery import build

GOOGLE_API_KEY = settings.GOOGLE_API_KEY
AIREL_FOLDER_ID = settings.AIREL_FOLDER_ID
OPENAI_API_KEY = settings.OPENAI_API_KEY


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


def openai_summarize_text(text):
    """
    Summary the given text using openai
    This is first to be used for summarizing long game logs (~13000 character) into a short summary
    """
    import openai

    openai.api_key = OPENAI_API_KEY

    text = (
        "Summarize the following game log from a game of dungeons and dragons into a few paragraphs:\n\n"
        + text
        + "\n\nSummary:"
    )

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=text,
        temperature=0.3,
        max_tokens=60,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        n=1,
    )
    return response["choices"][0]["text"]


