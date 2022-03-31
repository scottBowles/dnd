import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from .models import Association
from rest_framework import serializers
from graphene_django.filter import DjangoFilterConnectionField
from nucleus.utils import RelayCUD

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


class AssociationCUD(RelayCUD):
    field = "association"
    Node = AssociationNode
    model = Association
    serializer_class = AssociationSerializer

    class Input:
        name = graphene.String()
        description = graphene.String()
        image_id = graphene.String()
        thumbnail_id = graphene.String()


mutations = AssociationCUD()


class Mutation(graphene.ObjectType):
    association_create = mutations.create_mutation().Field()
    association_update = mutations.update_mutation().Field()
    association_patch = mutations.patch_mutation().Field()
    association_delete = mutations.delete_mutation().Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
