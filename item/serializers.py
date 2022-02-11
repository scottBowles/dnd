from rest_framework import serializers
from .models import Item, ArtifactTraits, ArmorTraits, WeaponTraits, EquipmentTraits

"""
Mixins provide fields specific to each one-to-one relationship.

"""


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtifactTraits
        fields = ["notes"]


class ArmorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArmorTraits
        fields = ["ac_bonus"]


class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeaponTraits
        fields = ["attack_bonus"]


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentTraits
        fields = ["brief_description"]


class ArtifactMixin(serializers.Serializer):
    artifact = ArtifactSerializer(required=False)

    class Meta:
        fields = ["artifact"]


class ArmorMixin(serializers.Serializer):
    armor = ArmorSerializer(required=False)

    class Meta:
        fields = ["armor"]


class WeaponMixin(serializers.Serializer):
    weapon = WeaponSerializer(required=False)

    class Meta:
        fields = ["weapon"]


class EquipmentMixin(serializers.Serializer):
    equipment = EquipmentSerializer(required=False)

    class Meta:
        fields = ["equipment"]


class ItemSerializer:
    pass


# class ItemSerializer(serializers.ModelSerializer):
#     artifact = serializers.SerializerMethodField(required=False)
#     armor = serializers.SerializerMethodField(required=False)
#     weapon = serializers.SerializerMethodField(required=False)
#     equipment = serializers.SerializerMethodField(required=False)

#     class Meta:
#         model = Item
#         fields = [
#             "id",
#             "name",
#             "description",
#             "artifact",
#             "armor",
#             "weapon",
#             "equipment",
#         ]

#     def get_artifact(self, obj):
#         return obj.artifact.pk if hasattr(obj, "artifact") else None

#     def get_armor(self, obj):
#         return obj.armor.pk if hasattr(obj, "armor") else None

#     def get_weapon(self, obj):
#         return obj.weapon.pk if hasattr(obj, "weapon") else None

#     def get_equipment(self, obj):
#         return obj.equipment.pk if hasattr(obj, "equipment") else None

#     def create(self, validated_data):
#         artifact_data = validated_data.pop("artifact", None)
#         armor_data = validated_data.pop("armor", None)
#         weapon_data = validated_data.pop("weapon", None)
#         equipment_data = validated_data.pop("equipment", None)

#         item = super().create(validated_data)

#         if artifact_data:
#             ArtifactTraits.objects.create(item=item, **artifact_data)
#         if armor_data:
#             ArmorTraits.objects.create(item=item, **armor_data)
#         if weapon_data:
#             WeaponTraits.objects.create(item=item, **weapon_data)
#         if equipment_data:
#             EquipmentTraits.objects.create(item=item, **equipment_data)

#         return item

#     def update(self, instance, validated_data):
#         artifact_data = validated_data.pop("artifact", None)
#         armor_data = validated_data.pop("armor", None)
#         weapon_data = validated_data.pop("weapon", None)
#         equipment_data = validated_data.pop("equipment", None)

#         if artifact_data:
#             ArtifactTraits.objects.update_or_create(
#                 item=instance, defaults=artifact_data
#             )
#         if armor_data:
#             ArmorTraits.objects.update_or_create(item=instance, defaults=armor_data)
#         if weapon_data:
#             WeaponTraits.objects.update_or_create(item=instance, defaults=weapon_data)
#         if equipment_data:
#             EquipmentTraits.objects.update_or_create(
#                 item=instance, defaults=equipment_data
#             )

#         super().update(instance, validated_data)

#         return instance
class ItemSerializerGQL(serializers.ModelSerializer):
    artifact = ArtifactSerializer(required=False)
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
        artifact_data = validated_data.pop("artifact", None)
        armor_data = validated_data.pop("armor", None)
        weapon_data = validated_data.pop("weapon", None)
        equipment_data = validated_data.pop("equipment", None)

        item = super().create(validated_data)

        if artifact_data:
            ArtifactTraits.objects.create(item=item, **artifact_data)
        if armor_data:
            ArmorTraits.objects.create(item=item, **armor_data)
        if weapon_data:
            WeaponTraits.objects.create(item=item, **weapon_data)
        if equipment_data:
            EquipmentTraits.objects.create(item=item, **equipment_data)

        return item

    def update(self, instance, validated_data):
        artifact_data = validated_data.pop("artifact", None)
        armor_data = validated_data.pop("armor", None)
        weapon_data = validated_data.pop("weapon", None)
        equipment_data = validated_data.pop("equipment", None)

        partial = self.context.get("partial", False)

        if partial:
            if artifact_data:
                ArtifactTraits.objects.update_or_create(
                    item=instance, defaults=artifact_data
                )
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
            self.update_or_remove(instance, ArtifactTraits, artifact_data)
            self.update_or_remove(instance, ArmorTraits, armor_data)
            self.update_or_remove(instance, WeaponTraits, weapon_data)
            self.update_or_remove(instance, EquipmentTraits, equipment_data)

        return super().update(instance, validated_data)


EXPAND_MIXINS = {
    "artifact": ArtifactMixin,
    "armor": ArmorMixin,
    "weapon": WeaponMixin,
    "equipment": EquipmentMixin,
}


def compose_item_serializer(**kwargs):
    """
    Takes the ItemSerializer as a base and adds mixins based on the kwargs.
    OneToOne fields are ids on the ItemSerializer, replaced by serialized fields
    by each mixin.
    """

    mixins = [
        EXPAND_MIXINS.get(k)
        for k in EXPAND_MIXINS
        if kwargs.get(k, False) or kwargs.get("all", False)
    ]

    class ComposedItemSerializer(*mixins, ItemSerializer):
        class Meta:
            model = Item
            fields = [
                val for c in mixins for val in c.Meta.fields
            ] + ItemSerializer.Meta.fields

    return ComposedItemSerializer
