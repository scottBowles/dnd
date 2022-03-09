from rest_framework import serializers
from .models import Character, Language, Script


class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = "__all__"


class LanguageSerializer(serializers.ModelSerializer):
    script = serializers.PrimaryKeyRelatedField(
        queryset=Script.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Language
        fields = "__all__"
