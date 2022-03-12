from .models import Item, Artifact, ArmorTraits, WeaponTraits, EquipmentTraits
from nucleus.utils import RelayModelSerializer

"""
Mixins provide fields specific to each one-to-one relationship.

"""


class ArmorSerializer(RelayModelSerializer):
    class Meta:
        model = ArmorTraits
        fields = ["ac_bonus"]


class WeaponSerializer(RelayModelSerializer):
    class Meta:
        model = WeaponTraits
        fields = ["attack_bonus"]


class EquipmentSerializer(RelayModelSerializer):
    class Meta:
        model = EquipmentTraits
        fields = ["brief_description"]


class ItemSerializer(RelayModelSerializer):
    armor = ArmorSerializer(required=False)
    weapon = WeaponSerializer(required=False)
    equipment = EquipmentSerializer(required=False)

    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "description",
            "artifact",
            "armor",
            "weapon",
            "equipment",
        ]

    def update_or_remove(self, instance, Model, data):
        if data:
            Model.objects.update_or_create(item=instance, defaults=data)
        else:
            Model.objects.filter(item=instance).delete()

    def create(self, validated_data):
        armor_data = validated_data.pop("armor", None)
        weapon_data = validated_data.pop("weapon", None)
        equipment_data = validated_data.pop("equipment", None)

        item = super().create(validated_data)

        if armor_data:
            ArmorTraits.objects.create(item=item, **armor_data)
        if weapon_data:
            WeaponTraits.objects.create(item=item, **weapon_data)
        if equipment_data:
            EquipmentTraits.objects.create(item=item, **equipment_data)

        return item

    def update(self, instance, validated_data):
        armor_data = validated_data.pop("armor", None)
        weapon_data = validated_data.pop("weapon", None)
        equipment_data = validated_data.pop("equipment", None)

        if self.partial:
            if armor_data:
                ArmorTraits.objects.update_or_create(item=instance, defaults=armor_data)
            if weapon_data:
                WeaponTraits.objects.update_or_create(
                    item=instance, defaults=weapon_data
                )
            if equipment_data:
                EquipmentTraits.objects.update_or_create(
                    item=instance, defaults=equipment_data
                )
        else:
            self.update_or_remove(instance, ArmorTraits, armor_data)
            self.update_or_remove(instance, WeaponTraits, weapon_data)
            self.update_or_remove(instance, EquipmentTraits, equipment_data)

        return super().update(instance, validated_data)


class ArtifactSerializer(RelayModelSerializer):
    items = ItemSerializer(many=True, required=False)

    class Meta:
        model = Artifact
        fields = [
            "name",
            "description",
            "items",
            "notes",
            "created",
            "updated",
        ]
