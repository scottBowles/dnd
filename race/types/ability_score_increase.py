from typing import Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models


@strawberry_django.type(models.AbilityScoreIncrease)
class AbilityScoreIncrease(relay.Node):
    ability_score: auto
    increase: auto


@strawberry_django.input(models.AbilityScoreIncrease)
class AbilityScoreIncreaseInput:
    ability_score: auto
    increase: auto


@strawberry_django.partial(models.AbilityScoreIncrease)
class AbilityScoreIncreaseInputPartial(strawberry_django.NodeInput):
    ability_score: auto
    increase: auto


@strawberry.type
class AbilityScoreIncreaseQuery:
    ability_score_increases: DjangoListConnection[AbilityScoreIncrease] = (
        strawberry_django.connection()
    )

    # @strawberry_django.connection(DjangoListConnection[AbilityScoreIncrease])
    # def ability_score_increases_connection_filtered(
    #     self, name_startswith: str
    # ) -> Iterable[AbilityScoreIncrease]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.AbilityScoreIncrease.objects.filter(
    #         name__startswith=name_startswith
    #     )


@strawberry.type
class AbilityScoreIncreaseMutation:
    create_ability_score_increase: AbilityScoreIncrease = (
        strawberry_django.mutations.create(
            AbilityScoreIncreaseInput, permission_classes=[IsStaff]
        )
    )
    update_ability_score_increase: AbilityScoreIncrease = (
        strawberry_django.mutations.update(
            AbilityScoreIncreaseInputPartial, permission_classes=[IsStaff]
        )
    )
    delete_ability_score_increase: AbilityScoreIncrease = (
        strawberry_django.mutations.delete(
            strawberry_django.NodeInput, permission_classes=[IsSuperuser]
        )
    )
