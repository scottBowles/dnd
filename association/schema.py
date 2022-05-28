import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from .models import Association
from rest_framework import serializers
from graphene_django.filter import DjangoFilterConnectionField
from nucleus.utils import (
    RelayCUD,
    ConcurrencyLockActions,
    ImageMutations,
    RelayPrimaryKeyRelatedField,
)
from character.models import NPC

from nucleus.utils import login_or_queryset_none


class AssociationNode(DjangoObjectType):
    locked_by_self = graphene.Boolean()

    def resolve_locked_by_self(self, info, **kwargs):
        return self.lock_user == info.context.user

    class Meta:
        model = Association
        fields = (
            "name",
            "description",
            "image_ids",
            "thumbnail_id",
            "created",
            "updated",
            "markdown_notes",
            "lock_user",
            "lock_time",
            "npcs",
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


class Query(graphene.ObjectType):
    association = relay.Node.Field(AssociationNode)
    associations = DjangoFilterConnectionField(AssociationNode)


class AssociationSerializer(serializers.ModelSerializer):
    npcs = RelayPrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=NPC.objects.all(),
        default=list,
    )

    class Meta:
        model = Association
        fields = "__all__"


class AssociationInput(graphene.InputObjectType):
    """
    For use where Association is nested in another object
    """

    name = graphene.String()
    description = graphene.String()
    image_ids = graphene.List(graphene.String)
    thumbnail_id = graphene.String()
    markdown_notes = graphene.String()
    npcs = graphene.List(graphene.ID)


class AssociationCUD(RelayCUD):
    field = "association"
    Node = AssociationNode
    model = Association
    serializer_class = AssociationSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_ids = graphene.List(graphene.String)
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()
        npcs = graphene.List(graphene.ID)


class AssociationConcurrencyLock(ConcurrencyLockActions):
    field = "association"
    Node = AssociationNode
    model = Association


class AssociationImageMutations(ImageMutations):
    field = "association"
    Node = AssociationNode
    model = Association


AssociationCUDMutations = AssociationCUD().get_mutation_class()
AssociationLockMutations = AssociationConcurrencyLock().get_mutation_class()
AssociationImageMutations = AssociationImageMutations().get_mutation_class()


class Mutation(
    AssociationCUDMutations,
    AssociationLockMutations,
    AssociationImageMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
