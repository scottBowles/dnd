from typing import Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models
from .language import Language


@strawberry_django.type(models.Script)
class Script(relay.Node):
    name: auto
    languages: DjangoListConnection[Language] = strawberry_django.connection()


@strawberry_django.input(models.Script)
class ScriptInput:
    name: auto
    languages: auto


@strawberry_django.partial(models.Script)
class ScriptInputPartial(strawberry_django.NodeInput):
    name: auto
    languages: auto


@strawberry.type
class ScriptQuery:
    scripts: DjangoListConnection[Script] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Script])
    # def scripts_connection_filtered(self, name_startswith: str) -> Iterable[Script]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Script.objects.filter(name__startswith=name_startswith)


@strawberry.type
class ScriptMutation:
    create_script: Script = strawberry_django.mutations.create(
        ScriptInput, permission_classes=[IsStaff]
    )
    update_script: Script = strawberry_django.mutations.update(
        ScriptInputPartial, permission_classes=[IsStaff]
    )
    delete_script: Script = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
