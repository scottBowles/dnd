from pprint import pprint
from rest_framework import viewsets
from .models import Artifact
from .serializers import ArtifactSerializer
from django.utils.decorators import classonlymethod
from item.models import Armor, Weapon, Equipment
from item.serializers import (
    ArmorSerializer,
    EquipmentSerializer,
    WeaponSerializer,
)


class ArtifactViewSet(viewsets.ModelViewSet):
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer

    def create(self, request, *args, **kwargs):
        from pprint import pprint

        related_items = request.data.pop("related_items")
        items = []
        for item in related_items:
            item_type = item.get("item_type")
            id = item.get("id")
            model_class = {
                "armor": Armor,
                "equipment": Equipment,
                "weapon": Weapon,
            }.get(item_type)
            serializer_class = {
                "armor": ArmorSerializer,
                "equipment": EquipmentSerializer,
                "weapon": WeaponSerializer,
            }.get(item_type)
            instance = model_class.objects.get(id=id)
            props = serializer_class(instance).data
            print("props: ", props)
            items.append({"item": {"item_type": item_type, **props}})
        request.data.update({"related_items": items})
        return super().create(request, *args, **kwargs)
