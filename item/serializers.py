from rest_framework import serializers
from .models import Item, Armor, Weapon, Equipment


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


class ArmorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Armor
        fields = "__all__"


class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weapon
        fields = "__all__"


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"
