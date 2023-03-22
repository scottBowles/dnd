from typing import Iterable, Optional
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models


@gql.django.type(models.AbilityScoreIncrease)
class AbilityScoreIncrease(relay.Node):
    ability_score: auto
    increase: auto


@gql.django.input(models.AbilityScoreIncrease)
class AbilityScoreIncreaseInput:
    ability_score: auto
    increase: auto


@gql.django.partial(models.AbilityScoreIncrease)
class AbilityScoreIncreaseInputPartial(gql.NodeInput):
    ability_score: auto
    increase: auto


@gql.type
class AbilityScoreIncreaseQuery:
    ability_score_increase: Optional[AbilityScoreIncrease] = gql.django.field()
    ability_score_increases: relay.Connection[
        AbilityScoreIncrease
    ] = gql.django.connection()

    @gql.django.connection
    def AbilityScoreIncreases_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[AbilityScoreIncrease]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.AbilityScoreIncrease.objects.filter(
            name__startswith=name_startswith
        )


@gql.type
class AbilityScoreIncreaseMutation:
    create_ability_score_increase: AbilityScoreIncrease = gql.django.create_mutation(
        AbilityScoreIncreaseInput
    )
    update_ability_score_increase: AbilityScoreIncrease = gql.django.update_mutation(
        AbilityScoreIncreaseInputPartial
    )
    delete_ability_score_increase: AbilityScoreIncrease = gql.django.delete_mutation(
        gql.NodeInput
    )
