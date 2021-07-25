from django.db import models
from django.contrib.auth.models import User
from rest_framework import serializers


class Character(models.Model):
    name = models.CharField(max_length=200)
    character_class = models.CharField(max_length=200)
    hit_points = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class CharacterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Character
