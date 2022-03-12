import graphene
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField

from .nodes import ItemNode, ArtifactNode


class ItemQuery(graphene.ObjectType):
    item = relay.Node.Field(ItemNode)
    items = DjangoFilterConnectionField(ItemNode)


class ArtifactQuery(graphene.ObjectType):
    artifact = relay.Node.Field(ArtifactNode)
    artifacts = DjangoFilterConnectionField(ArtifactNode)


class Query(ArtifactQuery, ItemQuery, graphene.ObjectType):
    pass
