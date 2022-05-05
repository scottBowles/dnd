import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from ..models import Item, ArmorTraits, WeaponTraits, EquipmentTraits, Artifact

from nucleus.utils import login_or_queryset_none


class ArmorTraitsNode(DjangoObjectType):
    class Meta:
        model = ArmorTraits
        fields = ("ac_bonus",)
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class WeaponTraitsNode(DjangoObjectType):
    class Meta:
        model = WeaponTraits
        fields = ("attack_bonus",)
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class EquipmentTraitsNode(DjangoObjectType):
    class Meta:
        model = EquipmentTraits
        fields = ("brief_description",)
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class ItemNode(DjangoObjectType):
    armor = graphene.Field(ArmorTraitsNode)
    weapon = graphene.Field(WeaponTraitsNode)
    equipment = graphene.Field(EquipmentTraitsNode)
    locked_by_self = graphene.Boolean()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = Item
        fields = (
            "id",
            "name",
            "description",
            "image_ids",
            "thumbnail_id",
            "created",
            "updated",
            "armor",
            "weapon",
            "equipment",
            "markdown_notes",
            "lock_user",
            "lock_time",
        )
        filter_fields = [
            "name",
            "description",
            "created",
            "updated",
        ]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class ArtifactNode(DjangoObjectType):
    locked_by_self = graphene.Boolean()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = Artifact
        fields = (
            "items",
            "notes",
            "name",
            "description",
            "image_ids",
            "thumbnail_id",
            "created",
            "updated",
            "markdown_notes",
            "lock_user",
            "lock_time",
        )
        filter_fields = [
            "name",
            "created",
        ]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset
