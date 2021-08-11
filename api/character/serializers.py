from rest_framework import serializers
from .models import Character


class CharacterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Character
        exclude = ("user",)
