# Generated by Django 4.1.7 on 2023-06-27 00:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("character", "0013_alter_character_aliases_alter_character_logs"),
        ("place", "0013_place_related_places_place_related_races"),
        ("race", "0010_race_related_races"),
        ("item", "0010_alter_artifact_aliases_alter_artifact_logs_and_more"),
        ("association", "0009_alter_association_aliases_alter_association_logs"),
    ]

    operations = [
        migrations.AddField(
            model_name="association",
            name="related_artifacts",
            field=models.ManyToManyField(
                blank=True, related_name="related_associations", to="item.artifact"
            ),
        ),
        migrations.AddField(
            model_name="association",
            name="related_associations",
            field=models.ManyToManyField(blank=True, to="association.association"),
        ),
        migrations.AddField(
            model_name="association",
            name="related_characters",
            field=models.ManyToManyField(
                blank=True,
                related_name="related_associations",
                to="character.character",
            ),
        ),
        migrations.AddField(
            model_name="association",
            name="related_items",
            field=models.ManyToManyField(
                blank=True, related_name="related_associations", to="item.item"
            ),
        ),
        migrations.AddField(
            model_name="association",
            name="related_places",
            field=models.ManyToManyField(
                blank=True, related_name="related_associations", to="place.place"
            ),
        ),
        migrations.AddField(
            model_name="association",
            name="related_races",
            field=models.ManyToManyField(
                blank=True, related_name="related_associations", to="race.race"
            ),
        ),
    ]