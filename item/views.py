from rest_framework import viewsets
from .models import Item, Artifact, Armor, Equipment, Weapon
from .serializers import compose_item_serializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    default_expand = []

    def get_serializer_class(self):
        if self.request.method == "GET":
            expand_list = self.request.query_params.getlist("expand", "")
            expand_list = expand_list or self.default_expand
            expand_args = {prop: True for prop in expand_list}
            return compose_item_serializer(**expand_args)
        return compose_item_serializer(all=True)


class ArtifactViewSet(ItemViewSet):
    queryset = Artifact.objects.all()
    default_expand = ["artifact"]


class EquipmentViewSet(ItemViewSet):
    queryset = Equipment.objects.all()
    default_expand = ["equipment"]


class ArmorViewSet(ItemViewSet):
    queryset = Armor.objects.all()
    default_expand = ["armor"]


class WeaponViewSet(ItemViewSet):
    queryset = Weapon.objects.all()
    default_expand = ["weapon"]
