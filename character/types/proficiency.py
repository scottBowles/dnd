from typing import TYPE_CHECKING, Annotated, Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from nucleus.relay import ListConnectionWithTotalCount

from .. import models

if TYPE_CHECKING:
    from character.types.character import Character


@strawberry_django.type(models.Proficiency)
class Proficiency(relay.Node):
    name: auto
    proficiency_type: auto
    description: auto
    characters: ListConnectionWithTotalCount[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()


@strawberry_django.input(models.Proficiency)
class ProficiencyInput:
    name: auto
    proficiency_type: auto
    description: auto
    characters: auto


@strawberry_django.partial(models.Proficiency)
class ProficiencyInputPartial(strawberry_django.NodeInput):
    name: auto
    proficiency_type: auto
    description: auto
    characters: auto


@strawberry.type
class ProficiencyQuery:
    proficiencies: ListConnectionWithTotalCount[Proficiency] = (
        strawberry_django.connection()
    )

    @strawberry_django.connection(ListConnectionWithTotalCount[Proficiency])
    def Proficiencys_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[Proficiency]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Proficiency.objects.filter(name__startswith=name_startswith)


@strawberry.type
class ProficiencyMutation:
    create_proficiency: Proficiency = strawberry_django.mutations.create(
        ProficiencyInput, permission_classes=[IsStaff]
    )
    update_proficiency: Proficiency = strawberry_django.mutations.update(
        ProficiencyInputPartial, permission_classes=[IsStaff]
    )
    delete_proficiency: Proficiency = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
