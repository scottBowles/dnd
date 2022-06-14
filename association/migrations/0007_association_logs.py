# Generated by Django 4.1a1 on 2022-06-13 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nucleus", "0002_entitylog"),
        ("association", "0006_alter_association_image_ids_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="association",
            name="logs",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(app_label)s_%(class)ss",
                to="nucleus.entitylog",
            ),
        ),
    ]
