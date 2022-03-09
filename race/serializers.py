from rest_framework import serializers
from .models import Race, AbilityScoreIncrease, Trait


class RaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Race
        fields = "__all__"


class AbilityScoreIncreaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbilityScoreIncrease
        fields = "__all__"

    def create(self, validated_data):
        ability_score = validated_data.get("ability_score")
        increase = validated_data.get("increase")
        return AbilityScoreIncrease.objects.get_or_create(
            ability_score=ability_score, increase=increase
        )[0]


class TraitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trait
        fields = "__all__"
