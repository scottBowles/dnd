# Generated by Django 4.0.1 on 2022-01-31 03:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0003_armortraits_equipmenttraits_item_weapontraits_and_more'),
        ('character', '0003_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='character',
            name='armor',
            field=models.ManyToManyField(blank=True, related_name='armor_inventories', through='character.InventoryArmor', to='item.Armor'),
        ),
        migrations.AlterField(
            model_name='character',
            name='equipment',
            field=models.ManyToManyField(blank=True, related_name='equipment_inventories', through='character.InventoryEquipment', to='item.Equipment'),
        ),
        migrations.AlterField(
            model_name='character',
            name='tool',
            field=models.ManyToManyField(blank=True, related_name='tool_inventories', through='character.InventoryTool', to='character.Tool'),
        ),
        migrations.AlterField(
            model_name='character',
            name='weapons',
            field=models.ManyToManyField(blank=True, related_name='weapon_inventories', through='character.InventoryWeapon', to='item.Weapon'),
        ),
    ]
