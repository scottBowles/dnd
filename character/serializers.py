from .models import Character, Language, Script, Feature, Skill, Proficiency
from nucleus.utils import RelayModelSerializer


class CharacterSerializer(RelayModelSerializer):
    class Meta:
        model = Character
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
