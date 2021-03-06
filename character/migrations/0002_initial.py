# Generated by Django 4.0.2 on 2022-03-21 03:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('race', '0001_initial'),
        ('item', '0001_initial'),
        ('character', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='npc',
            name='race',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='race.race'),
        ),
        migrations.AddField(
            model_name='language',
            name='script',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='character.script'),
        ),
        migrations.AddField(
            model_name='inventoryitem',
            name='character',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='ideal',
            name='character',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='flaw',
            name='character',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='classandlevel',
            name='character',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='character.character'),
        ),
        migrations.AddField(
            model_name='classandlevel',
            name='character_class',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='character.characterclass'),
        ),
        migrations.AddField(
            model_name='characterclass',
            name='proficiencies',
            field=models.ManyToManyField(related_name='classes', to='character.Proficiency'),
        ),
        migrations.AddField(
            model_name='character',
            name='armor',
            field=models.ManyToManyField(blank=True, related_name='armor_inventories', through='character.InventoryArmor', to='item.Armor'),
        ),
        migrations.AddField(
            model_name='character',
            name='background',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='character.background'),
        ),
        migrations.AddField(
            model_name='character',
            name='equipment',
            field=models.ManyToManyField(blank=True, related_name='equipment_inventories', through='character.InventoryEquipment', to='item.Equipment'),
        ),
        migrations.AddField(
            model_name='character',
            name='feats',
            field=models.ManyToManyField(blank=True, to='character.Feat'),
        ),
        migrations.AddField(
            model_name='character',
            name='features_and_traits',
            field=models.ManyToManyField(blank=True, related_name='characters', to='character.Feature'),
        ),
        migrations.AddField(
            model_name='character',
            name='proficiencies',
            field=models.ManyToManyField(blank=True, related_name='characters', to='character.Proficiency'),
        ),
        migrations.AddField(
            model_name='character',
            name='race',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='race.race'),
        ),
        migrations.AddField(
            model_name='character',
            name='tool',
            field=models.ManyToManyField(blank=True, related_name='tool_inventories', through='character.InventoryTool', to='character.Tool'),
        ),
    ]
