# Generated by Django 4.0.2 on 2022-03-08 00:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('race', '0003_alter_race_base_race'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='abilityscoreincrease',
            unique_together={('ability_score', 'increase')},
        ),
    ]