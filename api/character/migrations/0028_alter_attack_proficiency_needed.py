# Generated by Django 3.2.5 on 2021-08-25 02:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('character', '0027_attack_proficiency_needed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attack',
            name='proficiency_needed',
            field=models.ForeignKey(blank=True, limit_choices_to={'proficiency_type': 'weapon'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='character.proficiency'),
        ),
    ]
