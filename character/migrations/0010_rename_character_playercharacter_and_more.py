# Generated by Django 4.1.7 on 2023-04-12 19:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("item", "0008_alter_artifact_items"),
        ("race", "0007_race_logs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("association", "0007_association_logs"),
        ("character", "0009_npc_logs"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Character",
            new_name="PlayerCharacter",
        ),
        migrations.AlterField(
            model_name="language",
            name="script",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="languages",
                to="character.script",
            ),
        ),
        migrations.AlterField(
            model_name="npc",
            name="associations",
            field=models.ManyToManyField(
                blank=True, related_name="characters", to="association.association"
            ),
        ),
        migrations.AlterField(
            model_name="npc",
            name="race",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="characters",
                to="race.race",
            ),
        ),
    ]
