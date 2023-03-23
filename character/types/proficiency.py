from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from nucleus.permissions import IsStaff, IsSuperuser

from .. import models

if TYPE_CHECKING:
    from character.types.npc import Npc


@gql.django.type(models.Proficiency)
class Proficiency(relay.Node):
    name: auto
    proficiency_type: auto
    description: auto
    npcs: relay.Connection[
        Annotated["Npc", gql.lazy("character.types.npc")]
    ] = gql.django.connection()


@gql.django.input(models.Proficiency)
class ProficiencyInput:
    name: auto
    proficiency_type: auto
    description: auto
    npcs: auto


@gql.django.partial(models.Proficiency)
class ProficiencyInputPartial(gql.NodeInput):
    name: auto
    proficiency_type: auto
    description: auto
    npcs: auto


@gql.type
class ProficiencyQuery:
    proficiency: Optional[Proficiency] = gql.django.field()
    proficiencies: relay.Connection[Proficiency] = gql.django.connection()

    @gql.django.connection
    def Proficiencys_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[Proficiency]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Proficiency.objects.filter(name__startswith=name_startswith)


@gql.type
class ProficiencyMutation:
    create_proficiency: Proficiency = gql.django.create_mutation(
        ProficiencyInput, permission_classes=[IsStaff]
    )
    update_proficiency: Proficiency = gql.django.update_mutation(
        ProficiencyInputPartial, permission_classes=[IsStaff]
    )
    delete_proficiency: Proficiency = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )
