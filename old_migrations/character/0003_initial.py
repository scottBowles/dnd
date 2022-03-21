# Generated by Django 4.0.1 on 2022-01-29 02:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('character', '0002_initial'),
        ('item', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='character',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='character',
            name='weapons',
            field=models.ManyToManyField(blank=True, through='character.InventoryWeapon', to='item.Weapon'),
        ),
        migrations.AddField(
            model_name='bond',
            name='character',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='background',
            name='features',
            field=models.ManyToManyField(related_name='backgrounds', to='character.Feature'),
        ),
        migrations.AddField(
            model_name='background',
            name='languages',
            field=models.ManyToManyField(related_name='backgrounds', to='character.Language'),
        ),
        migrations.AddField(
            model_name='background',
            name='skill_proficiencies',
            field=models.ManyToManyField(related_name='backgrounds', to='character.Skill'),
        ),
        migrations.AddField(
            model_name='attack',
            name='character',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='attack',
            name='proficiency_needed',
            field=models.ForeignKey(blank=True, help_text="E.g., 'martial weapons'. May have to create the needed proficiency.", limit_choices_to={'proficiency_type': 'weapon'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='character.proficiency'),
        ),
        migrations.AddField(
            model_name='attack',
            name='weapon',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='item.weapon'),
        ),
        migrations.AddField(
            model_name='inventoryweapon',
            name='gear',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='item.weapon'),
        ),
        migrations.AddField(
            model_name='inventorytool',
            name='gear',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='character.tool'),
        ),
        migrations.AddField(
            model_name='inventoryequipment',
            name='gear',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='item.equipment'),
        ),
        migrations.AddField(
            model_name='inventoryarmor',
            name='gear',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='item.armor'),
        ),
    ]
