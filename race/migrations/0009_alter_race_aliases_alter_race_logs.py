# Generated by Django 4.1.7 on 2023-05-20 03:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nucleus", "0011_alias_is_primary"),
        ("race", "0008_race_aliases"),
    ]

    operations = [
        migrations.AlterField(
            model_name="race",
            name="aliases",
            field=models.ManyToManyField(
                blank=True, related_name="base_%(class)ss", to="nucleus.alias"
            ),
        ),
        migrations.AlterField(
            model_name="race",
            name="logs",
            field=models.ManyToManyField(
                blank=True, related_name="%(class)ss", to="nucleus.gamelog"
            ),
        ),
    ]
