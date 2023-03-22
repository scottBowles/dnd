from typing import Optional
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


@gql.django.partial(models.GameLog)
class GameLogInputPartial(gql.NodeInput):
    url: auto


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
    create_game_log: GameLog = gql.django.create_mutation(GameLogInput)
    update_game_log: GameLog = gql.django.update_mutation(GameLogInputPartial)
    delete_game_log: GameLog = gql.django.delete_mutation(gql.NodeInput)

    @gql.django.input_mutation
    def add_entity_log(
        self,
        info,
        entity_id: gql.relay.GlobalID,
        log_url: Optional[str],
        log_id: Optional[gql.relay.GlobalID],
    ) -> GameLog:
        entity = entity_id.resolve_node(info)

        if log_id is not None:
            log = log_id.resolve_node(info)
        else:
            google_id = models.GameLog.get_id_from_url(log_url)
            log = models.GameLog.objects.get_or_create(google_id=google_id)[0]

        entity.logs.add(log)
        entity.save()
        return log

    @gql.mutation
    def remove_entity_log(self, info, input: RemoveEntityLogInput) -> GameLog:
        log = input.log_id.resolve_node(info)
        entity = input.entity_id.resolve_node(info)
        entity.logs.remove(log)
        entity.save()
        return log
