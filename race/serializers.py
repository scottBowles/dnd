from .models import Race, AbilityScoreIncrease, Trait
from nucleus.utils import RelayModelSerializer, RelayPrimaryKeyRelatedField


class RaceSerializer(RelayModelSerializer):
    subraces = RelayPrimaryKeyRelatedField(
        queryset=Race.objects.all(), many=True, default=list
    )

    class Meta:
        model = Race
        fields = "__all__"


class AbilityScoreIncreaseSerializer(RelayModelSerializer):
    class Meta:
        model = AbilityScoreIncrease
        fields = "__all__"

    def create(self, validated_data):
        ability_score = validated_data.get("ability_score")
        increase = validated_data.get("increase")
        return AbilityScoreIncrease.objects.get_or_create(
            ability_score=ability_score, increase=increase
        )[0]


class TraitSerializer(RelayModelSerializer):
    class Meta:
        model = Trait
        fields = "__all__"
