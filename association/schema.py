import graphene
from graphene_django import DjangoObjectType
from .models import Association


class AssociationType(DjangoObjectType):
    class Meta:
        model = Association
        fields = ("id", "name", "description", "created", "updated")


class Query(graphene.ObjectType):
    associations = graphene.List(AssociationType)
    association_by_id = graphene.Field(AssociationType, id=graphene.Int())

    def resolve_associations(self, info):
        return Association.objects.all()

    def resolve_association_by_id(self, info, **kwargs):
        id = kwargs.get("id")
        return Association.objects.filter(pk=id).first()


schema = graphene.Schema(query=Query)
