from rest_framework import serializers
from generic_relations.relations import GenericRelatedField
from generic_relations.serializers import GenericModelSerializer

from item.models import Armor, Weapon, Equipment
from item.serializers import (
    ArmorSerializer,
    EquipmentSerializer,
    WeaponSerializer,
)
from .models import Artifact, ArtifactItem


class ItemField(GenericRelatedField):
    def get_deserializer_for_data(self, value):
        print("value", value)
        item_type = value.get("item_type")
        serializer = {
            "armor": ArmorSerializer(),
            "equipment": EquipmentSerializer(),
            "weapon": WeaponSerializer(),
        }.get(item_type)
        return serializer


class ArtifactItemSerializer(serializers.ModelSerializer):
    item = GenericRelatedField(
        {
            Armor: serializers.HyperlinkedRelatedField(
                queryset=Armor.objects.all(),
                view_name="armor-detail",
            ),
            Equipment: serializers.HyperlinkedRelatedField(
                queryset=Equipment.objects.all(),
                view_name="equipment-detail",
            ),
            Weapon: serializers.HyperlinkedRelatedField(
                queryset=Weapon.objects.all(),
                view_name="weapon-detail",
            ),
        }
    )

    class Meta:
        model = ArtifactItem
        fields = ("item", "artifact")
        read_only_fields = ("artifact",)


class ArtifactSerializer(serializers.ModelSerializer):
    related_items = ArtifactItemSerializer(many=True)

    # def get_item(self, data):
    #     print("data: ", data)
    #     item_type = data.get("item_type")
    #     id = data.get("id")
    #     model_class = {
    #         "armor": Armor,
    #         "equipment": Equipment,
    #         "weapon": Weapon,
    #     }.get(item_type)
    #     instance = model_class.objects.get(id=id)
    #     return instance

    def create(self, validated_data):
        print("VALIDATED DATA", validated_data)
        related_items = validated_data.pop("related_items")
        instance = super().create(validated_data)
        print("related_items: ", related_items)
        for item in related_items:
            print("ITEM:", item)
            serializer = ArtifactItemSerializer(data={"artifact": instance, "item": ""})
            print("GOT SERIALIZER")
            serializer.is_valid(raise_exception=True)
            print("SERIALIZER IS VALID")
            serializer.save()
            print("SERIALIZER IS SAVED")
            # i = self.get_item(item["item"])
            # ArtifactItem.objects.get_or_create(artifact=instance, item=i.__dict__)
        return instance

    # def update(self, instance, validated_data):
    #     related_items = validated_data.pop("related_items")
    #     instance = super().update(instance, validated_data)
    #     for item in related_items:
    #         ArtifactItem.objects.update_or_create(
    #             artifact=instance, item=item["item"], defaults=item
    #         )
    #     return instance

    class Meta:
        model = Artifact
        fields = (
            "id",
            "name",
            "description",
            "slug",
            "created",
            "updated",
            "related_items",
        )
