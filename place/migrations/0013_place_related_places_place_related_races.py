# Generated by Django 4.1.7 on 2023-06-27 00:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("race", "0010_race_related_races"),
        ("place", "0012_alter_export_aliases_alter_export_logs_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="place",
            name="related_places",
            field=models.ManyToManyField(blank=True, to="place.place"),
        ),
        migrations.AddField(
            model_name="place",
            name="related_races",
            field=models.ManyToManyField(
                blank=True, related_name="related_places", to="race.race"
            ),
        ),
    ]
