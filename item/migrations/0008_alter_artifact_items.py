# Generated by Django 4.1b1 on 2022-06-28 21:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("item", "0007_artifact_logs_item_logs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="artifact",
            name="items",
            field=models.ManyToManyField(
                blank=True, related_name="artifacts", to="item.item"
            ),
        ),
    ]