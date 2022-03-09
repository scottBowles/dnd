from .models import Character, Language
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
