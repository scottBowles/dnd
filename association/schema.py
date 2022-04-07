import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from .models import Association
from rest_framework import serializers
from graphene_django.filter import DjangoFilterConnectionField
from nucleus.utils import RelayCUD, ConcurrencyLockActions

from nucleus.utils import login_or_queryset_none


class AssociationNode(DjangoObjectType):
    class Meta:
        model = Association
        fields = (
            "name",
            "description",
            "image_id",
            "thumbnail_id",
            "created",
            "updated",
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


class Query(graphene.ObjectType):
    association = relay.Node.Field(AssociationNode)
    associations = DjangoFilterConnectionField(AssociationNode)


class AssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Association
        fields = "__all__"


class AssociationInput(graphene.InputObjectType):
    """
    For use where Association is nested in another object
    """

    name = graphene.String()
    description = graphene.String()
    image_id = graphene.String()
    thumbnail_id = graphene.String()
    markdown_notes = graphene.String()


class AssociationCUD(RelayCUD):
    field = "association"
    Node = AssociationNode
    model = Association
    serializer_class = AssociationSerializer
    enforce_lock = True

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_id = graphene.String()
        thumbnail_id = graphene.String()
        markdown_notes = graphene.String()


class AssociationConcurrencyLock(ConcurrencyLockActions):
    field = "association"
    model = Association


AssociationCUDMutations = AssociationCUD().get_mutation_class()
AssociationLockMutations = AssociationConcurrencyLock().get_mutation_class()


class Mutation(AssociationCUDMutations, AssociationLockMutations, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
