from typing import TYPE_CHECKING, Annotated, Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models

if TYPE_CHECKING:
    from .script import Script


@strawberry_django.type(models.Language)
class Language(relay.Node):
    name: auto
    description: auto
    script: Annotated["Script", strawberry.lazy(".script")]


@strawberry_django.input(models.Language)
class LanguageInput:
    name: auto
    description: auto
    script: auto


@strawberry_django.partial(models.Language)
class LanguageInputPartial(strawberry_django.NodeInput):
    name: auto
    description: auto
    script: auto


@strawberry.type
class LanguageQuery:
    languages: DjangoListConnection[Language] = strawberry_django.connection()

    @strawberry_django.connection(DjangoListConnection[Language])
    def Languages_connection_filtered(self, name_startswith: str) -> Iterable[Language]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Language.objects.filter(name__startswith=name_startswith)


@strawberry.type
class LanguageMutation:
    create_language: Language = strawberry_django.mutations.create(
        LanguageInput, permission_classes=[IsStaff]
    )
    update_language: Language = strawberry_django.mutations.update(
        LanguageInputPartial, permission_classes=[IsStaff]
    )
    delete_language: Language = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
