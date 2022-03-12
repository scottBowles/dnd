# Generated by Django 4.0.2 on 2022-03-12 01:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('item', '0006_alter_armortraits_ac_bonus_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='artifacttraits',
            name='item',
        ),
        migrations.DeleteModel(
            name='Artifact',
        ),
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('items', models.ManyToManyField(related_name='artifacts', to='item.Item')),
            ],
        ),
        migrations.DeleteModel(
            name='ArtifactTraits',
        ),
    ]
