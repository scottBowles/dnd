# Generated by Django 4.0.1 on 2022-01-29 04:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('artifact', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='artifactitem',
            old_name='item_content_type',
            new_name='content_type',
        ),
        migrations.RenameField(
            model_name='artifactitem',
            old_name='item_object_id',
            new_name='object_id',
        ),
    ]
