import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.contrib.auth import get_user_model

from nucleus.utils import login_or_queryset_none
from nucleus.models import GameLog


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


class GameLogNode(DjangoObjectType):
    class Meta:
        model = GameLog
        fields = (
            "id",
            "title",
            "url",
        )
        filter_fields = ("title",)
        interfaces = (relay.Node,)

    @classmethod
    @login_or_queryset_none
    def get_queryset(cls, queryset, info):
        return queryset


class AddEntityLogMutation(relay.ClientIDMutation):
    class Input:
        entity_id = graphene.ID()
        log_id = graphene.ID()
        log_url = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.String()
    log = graphene.Field(GameLogNode)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            entity_id = input.get("entity_id")
            log_id = input.get("log_id", None)
            log_url = input.get("log_url", None)
            if log_id is not None:
                log = relay.Node.get_node_from_global_id(info, log_id)
            else:
                google_id = GameLog.get_id_from_url(log_url)
                log = GameLog.objects.get_or_create(google_id=google_id)[0]
            entity = relay.Node.get_node_from_global_id(info, entity_id)
            entity.logs.add(log)
            entity.save()
            return AddEntityLogMutation(ok=True, log=log)
        except Exception as e:
            return AddEntityLogMutation(ok=False, errors=str(e))


class RemoveEntityLogMutation(relay.ClientIDMutation):
    class Input:
        log_id = graphene.ID()
        entity_id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.String()

    @classmethod
    def mutate(cls, root, info, input):
        try:
            log_id = input.get("log_id")
            entity_id = input.get("entity_id")
            log = relay.Node.get_node_from_global_id(info, log_id)
            entity = relay.Node.get_node_from_global_id(info, entity_id)
            entity.logs.remove(log)
            entity.save()
            return RemoveEntityLogMutation(ok=True)
        except Exception as e:
            return RemoveEntityLogMutation(ok=False, errors=str(e))


class Query(graphene.ObjectType):
    user = relay.Node.Field(UserNode)
    users = DjangoFilterConnectionField(UserNode)
    me = graphene.Field(UserNode)
    game_logs = DjangoFilterConnectionField(GameLogNode)

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Not logged in!")
        return user


class Mutation(graphene.ObjectType):
    add_entity_log = AddEntityLogMutation.Field()
    remove_entity_log = RemoveEntityLogMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
