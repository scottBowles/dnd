from typing import Optional

from nucleus.permissions import IsStaff, IsSuperuser
from .. import models
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto


@gql.django.type(models.GameLog)
class GameLog(relay.Node):
    url: auto
    name: auto
    google_id: auto


@gql.django.input(models.GameLog)
class GameLogInput:
    url: auto


@gql.input
class AddEntityLogInput:
    entity_id: gql.relay.GlobalID
    log_url: Optional[str] = gql.UNSET
    log_id: Optional[gql.relay.GlobalID] = gql.UNSET


@gql.input
class RemoveEntityLogInput:
    entity_id: gql.relay.GlobalID
    log_id: gql.relay.GlobalID


@gql.type
class GameLogQuery:
    game_log: Optional[GameLog] = gql.django.field()
    game_logs: relay.Connection[GameLog] = gql.django.connection()


@gql.type
class GameLogMutation:
    create_game_log: GameLog = gql.django.create_mutation(
        GameLogInput, permission_classes=[IsStaff]
    )
    update_game_log: GameLog = gql.django.update_mutation(
        GameLogInputPartial, permission_classes=[IsStaff]
    )
    delete_game_log: GameLog = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )
