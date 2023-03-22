from typing import Iterable, Optional
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models
from .language import Language


@gql.django.type(models.Script)
class Script(relay.Node):
    name: auto
    languages: relay.Connection[Language] = gql.django.connection()


@gql.django.input(models.Script)
class ScriptInput:
    name: auto
    languages: auto


@gql.django.partial(models.Script)
class ScriptInputPartial(gql.NodeInput):
    name: auto
    languages: auto


@gql.type
class ScriptQuery:
    script: Optional[Script] = gql.django.field()
    scripts: relay.Connection[Script] = gql.django.connection()

    @gql.django.connection
    def Scripts_connection_filtered(self, name_startswith: str) -> Iterable[Script]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Script.objects.filter(name__startswith=name_startswith)


@gql.type
class ScriptMutation:
    create_script: Script = gql.django.create_mutation(ScriptInput)
    update_script: Script = gql.django.update_mutation(ScriptInputPartial)
    delete_script: Script = gql.django.delete_mutation(gql.NodeInput)
