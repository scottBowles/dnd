import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.contrib.auth import get_user_model

from nucleus.utils import login_or_queryset_none


class UserNode(DjangoObjectType):
    class Meta:
        model = get_user_model()
        fields = (
            "isDM",
            "username",
            "email",
            "first_name",
            "last_name",
        )
        filter_fields = [
            "isDM",
        ]
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class Query(graphene.ObjectType):
    user = relay.Node.Field(UserNode)
    users = DjangoFilterConnectionField(UserNode)
    me = graphene.Field(UserNode)

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Not logged in!")
        return user


schema = graphene.Schema(query=Query)
