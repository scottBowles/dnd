# Generated by Django 4.0.3 on 2022-03-22 22:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('race', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='race',
            name='thumbnail_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
