# Generated by Django 4.1.7 on 2025-06-22 01:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("nucleus", "0016_gamelog_audio_session_notes_gamelog_last_game_log_and_more"),
        ("transcription", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="audiotranscript",
            name="session",
        ),
        migrations.AddField(
            model_name="audiotranscript",
            name="session_audio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="audio_transcripts",
                to="nucleus.sessionaudio",
            ),
        ),
        migrations.DeleteModel(
            name="TranscriptionSession",
        ),
    ]
