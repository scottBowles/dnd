# Generated by Django 4.1a1 on 2022-06-13 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nucleus", "0002_entitylog"),
        ("race", "0006_alter_race_image_ids_alter_race_markdown_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="race",
            name="logs",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(app_label)s_%(class)ss",
                to="nucleus.entitylog",
            ),
        ),
    ]
