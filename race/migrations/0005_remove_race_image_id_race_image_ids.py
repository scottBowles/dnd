# Generated by Django 4.0.3 on 2022-04-24 19:02

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('race', '0004_race_lock_time_race_lock_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='race',
            name='image_id',
        ),
        migrations.AddField(
            model_name='race',
            name='image_ids',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), default=list, size=None),
        ),
    ]
