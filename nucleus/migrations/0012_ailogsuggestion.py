# Generated by Django 4.1.7 on 2023-05-30 01:05

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("nucleus", "0011_alias_is_primary"),
    ]

    operations = [
        migrations.CreateModel(
            name="AiLogSuggestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=512, null=True)),
                ("brief", models.TextField(blank=True, null=True)),
                ("synopsis", models.TextField(blank=True, null=True)),
                (
                    "associations",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=512),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "characters",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=512),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "items",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=512),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "places",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=512),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "races",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=512),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "log",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="nucleus.gamelog",
                    ),
                ),
            ],
        ),
    ]
