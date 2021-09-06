from rest_framework import serializers
from .models import Armor, Equipment, Weapon


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"


class ArmorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Armor
        fields = "__all__"


class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weapon
        fields = "__all__"
