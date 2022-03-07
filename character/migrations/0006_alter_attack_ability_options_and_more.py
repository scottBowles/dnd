# Generated by Django 4.0.2 on 2022-03-05 18:50

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('character', '0005_npc_npcfact'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attack',
            name='ability_options',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('STRENGTH', 'Strength'), ('DEXTERITY', 'Dexterity'), ('CONSTITUTION', 'Constitution'), ('INTELLIGENCE', 'Intelligence'), ('WISDOM', 'Wisdom'), ('CHARISMA', 'Charisma')], max_length=12), default=list, help_text="Comma separated ability scores. Usually 'strength' or 'dexterity'. With finesse: 'strength, dexterity'.", size=None),
        ),
        migrations.AlterField(
            model_name='attack',
            name='proficiency_needed',
            field=models.ForeignKey(blank=True, help_text="E.g., 'martial weapons'. May have to create the needed proficiency.", limit_choices_to={'proficiency_type': 'WEAPON'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='character.proficiency'),
        ),
        migrations.AlterField(
            model_name='character',
            name='size',
            field=models.CharField(blank=True, choices=[('TINY', 'Tiny'), ('SMALL', 'Small'), ('MEDIUM', 'Medium'), ('LARGE', 'Large'), ('HUGE', 'Huge'), ('GARGANTUAN', 'Gargantuan')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='npc',
            name='size',
            field=models.CharField(blank=True, choices=[('TINY', 'Tiny'), ('SMALL', 'Small'), ('MEDIUM', 'Medium'), ('LARGE', 'Large'), ('HUGE', 'Huge'), ('GARGANTUAN', 'Gargantuan')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='proficiency',
            name='proficiency_type',
            field=models.CharField(choices=[('ARMOR', 'Armor'), ('WEAPON', 'Weapon'), ('SKILL', 'Skill'), ('TOOL', 'Tool'), ('LANGUAGE', 'Language'), ('ABILITY', 'Ability'), ('OTHER', 'Other')], default='OTHER', max_length=8),
        ),
        migrations.AlterField(
            model_name='skill',
            name='related_ability',
            field=models.CharField(choices=[('STRENGTH', 'Strength'), ('DEXTERITY', 'Dexterity'), ('CONSTITUTION', 'Constitution'), ('INTELLIGENCE', 'Intelligence'), ('WISDOM', 'Wisdom'), ('CHARISMA', 'Charisma')], max_length=12),
        ),
        migrations.DeleteModel(
            name='NPCFact',
        ),
    ]
