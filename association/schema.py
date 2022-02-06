import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from .models import Association
from rest_framework import serializers
from graphene_django.filter import DjangoFilterConnectionField
from nucleus.utils import RelayCUD


class AssociationNode(DjangoObjectType):
    class Meta:
        model = Association
        fields = ("name", "description", "created", "updated")
        filter_fields = [
            "name",
            "description",
            "created",
            "updated",
        ]
        interfaces = (relay.Node,)


class Query(graphene.ObjectType):
    association = relay.Node.Field(AssociationNode)
    associations = DjangoFilterConnectionField(AssociationNode)


class AssociationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Association
        fields = "__all__"


class AssociationMutations(RelayCUD):
    class Input:
        name = graphene.String()
        description = graphene.String()

    class Meta:
        model = Association
        serializer = AssociationSerializer


mutations = AssociationMutations("association", AssociationNode)


class Mutation(graphene.ObjectType):
    association_create = mutations.create_mutation().Field()
    association_update = mutations.update_mutation().Field()
    association_delete = mutations.delete_mutation().Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
