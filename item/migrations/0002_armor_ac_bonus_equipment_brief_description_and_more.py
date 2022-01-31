# Generated by Django 4.0.1 on 2022-01-31 00:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='armor',
            name='ac_bonus',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='equipment',
            name='brief_description',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='weapon',
            name='attack_bonus',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
