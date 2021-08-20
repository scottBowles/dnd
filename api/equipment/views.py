from rest_framework import viewsets
from .models import Armor, Equipment, Weapon
from .serializers import ArmorSerializer, EquipmentSerializer, WeaponSerializer


# Create your views here.
class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class ArmorViewSet(viewsets.ModelViewSet):
    queryset = Armor.objects.all()
    serializer_class = ArmorSerializer


class WeaponViewSet(viewsets.ModelViewSet):
    queryset = Weapon.objects.all()
    serializer_class = WeaponSerializer
