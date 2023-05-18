import datetime
from typing import TYPE_CHECKING, Annotated, Optional

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types.entity import Lockable, locked_by_self
from nucleus.types.user import User
from .. import models
from strawberry_django_plus import gql
from strawberry_django_plus.mutations import resolvers
from strawberry_django_plus.gql import relay, auto

if TYPE_CHECKING:
    from place.types.place import Place


@gql.django.type(models.GameLog)
class GameLog(Lockable, relay.Node):
    url: auto
    title: auto
    google_id: auto
    game_date: auto
    brief: auto
    synopsis: auto
    places_set_in: relay.Connection[
        Annotated["Place", gql.lazy("place.types.place")]
    ] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = gql.field(resolver=locked_by_self)


@gql.django.input(models.GameLog)
class GetOrCreateGameLogInput:
    url: auto
    lock: bool = False


@gql.input
class AddEntityLogInput:
    entity_id: gql.relay.GlobalID
    log_url: Optional[str] = gql.UNSET
    log_id: Optional[gql.relay.GlobalID] = gql.UNSET


@gql.django.partial(models.GameLog)
class GameLogInputPartial(gql.NodeInput):
    title: auto
    game_date: auto
    brief: auto
    synopsis: auto
    places_set_in: auto


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
    @gql.django.mutation(permission_classes=[IsStaff])
    def get_or_create_game_log(self, info, input: GetOrCreateGameLogInput) -> GameLog:
        google_id = models.GameLog.get_id_from_url(input.url)
        log = models.GameLog.objects.get_or_create(google_id=google_id)[0]
        if input.lock:
            log.lock(info.context.request.user)
        return log

    @gql.django.mutation(permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked])
    def update_gamelog(
        self,
        info,
        input: GameLogInputPartial,
    ) -> GameLog:
        data = vars(input)
        node_id = data.pop("id")
        gameLog: models.GameLog = node_id.resolve_node(info, ensure_type=models.GameLog)
        resolvers.update(info, gameLog, resolvers.parse_input(info, data))
        gameLog.release_lock(info.context.request.user)
        return gameLog

    delete_game_log: GameLog = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def gamelog_lock(
        self,
        info,
        id: gql.relay.GlobalID,
    ) -> GameLog:
        gamelog = id.resolve_node(info)
        gamelog = gamelog.lock(info.context.request.user)
        return gamelog

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def gamelog_release_lock(self, info, id: gql.relay.GlobalID) -> GameLog:
        gamelog = id.resolve_node(info)
        gamelog = gamelog.release_lock(info.context.request.user)
        return gamelog
