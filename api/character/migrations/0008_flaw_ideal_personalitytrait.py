# Generated by Django 3.2.5 on 2021-08-14 18:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('character', '0007_auto_20210814_1744'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalityTrait',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=500)),
                ('text', models.TextField(default='')),
                ('character', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='character.character')),
            ],
        ),
        migrations.CreateModel(
            name='Ideal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=500)),
                ('text', models.TextField(default='')),
                ('character', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='character.character')),
            ],
        ),
        migrations.CreateModel(
            name='Flaw',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=500)),
                ('text', models.TextField(default='')),
                ('character', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='character.character')),
            ],
        ),
    ]