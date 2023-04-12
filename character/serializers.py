from .models import (
    PlayerCharacter,
    Language,
    Script,
    Feature,
    Skill,
    Proficiency,
    Character,
)
from nucleus.utils import RelayModelSerializer


class CharacterSerializer(RelayModelSerializer):
    class Meta:
        model = PlayerCharacter
        fields = "__all__"


class LanguageSerializer(RelayModelSerializer):
    class Meta:
        model = Language
        fields = (
            "id",
            "name",
            "description",
            "script",
        )


class ScriptSerializer(RelayModelSerializer):
    class Meta:
        model = Script
        fields = (
            "id",
            "name",
        )


class FeatureSerializer(RelayModelSerializer):
    class Meta:
        model = Feature
        fields = ("id", "name", "description")


class SkillSerializer(RelayModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "description", "related_ability", "custom")


class ProficiencySerializer(RelayModelSerializer):
    class Meta:
        model = Proficiency
        fields = ("id", "name", "description", "proficiency_type")


class NPCSerializer(RelayModelSerializer):
    class Meta:
        model = Character
        fields = "__all__"
