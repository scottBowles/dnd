# Generated by Django 4.0.2 on 2022-03-21 03:36

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='name', unique=True, verbose_name='slug')),
                ('image_id', models.CharField(blank=True, max_length=255, null=True)),
                ('thumbnail_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='image ids')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WeaponTraits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attack_bonus', models.IntegerField(blank=True, default=0)),
                ('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='weapon', to='item.item')),
            ],
        ),
        migrations.CreateModel(
            name='EquipmentTraits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brief_description', models.TextField(blank=True, default='')),
                ('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='equipment', to='item.item')),
            ],
        ),
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('slug', django_extensions.db.fields.AutoSlugField(blank=True, editable=False, populate_from='name', unique=True, verbose_name='slug')),
                ('image_id', models.CharField(blank=True, max_length=255, null=True)),
                ('thumbnail_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='image ids')),
                ('notes', models.TextField(blank=True, null=True)),
                ('items', models.ManyToManyField(related_name='artifacts', to='item.Item')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ArmorTraits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ac_bonus', models.IntegerField(blank=True, default=0)),
                ('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='armor', to='item.item')),
            ],
        ),
        migrations.CreateModel(
            name='Armor',
            fields=[
            ],
            options={
                'verbose_name_plural': 'Armor',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('item.item',),
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
            ],
            options={
                'verbose_name_plural': 'Equipment',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('item.item',),
        ),
        migrations.CreateModel(
            name='Weapon',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('item.item',),
        ),
    ]
