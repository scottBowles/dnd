# Generated by Django 4.0.3 on 2022-04-02 22:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('race', '0003_race_markdown_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='race',
            name='lock_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='race',
            name='lock_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_lock_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
