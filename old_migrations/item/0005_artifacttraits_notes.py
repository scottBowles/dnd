# Generated by Django 4.0.1 on 2022-01-31 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0004_artifact_remove_item_is_artifact_artifacttraits'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifacttraits',
            name='notes',
            field=models.TextField(default=''),
        ),
    ]