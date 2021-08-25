# Generated by Django 3.2.5 on 2021-08-25 01:58

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('character', '0025_auto_20210824_1315'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attack',
            name='attack_ability_options',
        ),
        migrations.RemoveField(
            model_name='attack',
            name='damage_ability_options',
        ),
        migrations.AddField(
            model_name='attack',
            name='ability_options',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('strength', 'Strength'), ('dexterity', 'Dexterity'), ('constitution', 'Constitution'), ('intelligence', 'Intelligence'), ('wisdom', 'Wisdom'), ('charisma', 'Charisma')], max_length=12), default=list, help_text="Comma separated ability scores. Usually 'strength' or 'dexterity'. With finesse: 'strength, dexterity'.", size=None),
        ),
        migrations.AlterField(
            model_name='attack',
            name='properties',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='attack',
            name='range',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
