from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from nucleus.permissions import IsStaff, IsSuperuser

from .. import models

if TYPE_CHECKING:
    from .script import Script


@gql.django.type(models.Language)
class Language(relay.Node):
    name: auto
    description: auto
    script: Annotated["Script", gql.lazy(".script")]


@gql.django.input(models.Language)
class LanguageInput:
    name: auto
    description: auto
    script: auto


@gql.django.partial(models.Language)
class LanguageInputPartial(gql.NodeInput):
    name: auto
    description: auto
    script: auto


@gql.type
class LanguageQuery:
    language: Optional[Language] = gql.django.field()
    languages: relay.Connection[Language] = gql.django.connection()

    @gql.django.connection
    def Languages_connection_filtered(self, name_startswith: str) -> Iterable[Language]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Language.objects.filter(name__startswith=name_startswith)


@gql.type
class LanguageMutation:
    create_language: Language = gql.django.create_mutation(
        LanguageInput, permission_classes=[IsStaff]
    )
    update_language: Language = gql.django.update_mutation(
        LanguageInputPartial, permission_classes=[IsStaff]
    )
    delete_language: Language = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )
