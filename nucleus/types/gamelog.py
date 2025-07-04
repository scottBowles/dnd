import datetime
from typing import TYPE_CHECKING, Annotated, List, Optional

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.relay import ListConnectionWithTotalCount
from nucleus.types.entity import Lockable, locked_by_self
from nucleus.types.user import User

from .. import models

if TYPE_CHECKING:
    from association.types import Association
    from character.types.character import Character
    from item.types.artifact import Artifact
    from item.types.item import Item
    from place.types.place import Place
    from race.types.race import Race


@strawberry.type
class GameLogAiSummary:
    title: str
    brief: str
    synopsis: str
    places: List[str]
    found_places: List[Annotated["Place", strawberry.lazy("place.types.place")]]
    characters: List[str]
    found_characters: List[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ]
    races: List[str]
    found_races: List[Annotated["Race", strawberry.lazy("race.types.race")]]
    associations: List[str]
    found_associations: List[
        Annotated["Association", strawberry.lazy("association.types")]
    ]
    items: List[str]
    found_items: List[Annotated["Item", strawberry.lazy("item.types.item")]]
    artifacts: List[str]
    found_artifacts: List[Annotated["Artifact", strawberry.lazy("item.types.artifact")]]


@strawberry.type
class CombinedGameLogAiSummary:
    titles: List[str]
    briefs: List[str]
    synopses: List[str]
    places: List[str]
    found_places: List[Annotated["Place", strawberry.lazy("place.types.place")]]
    characters: List[str]
    found_characters: List[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ]
    races: List[str]
    found_races: List[Annotated["Race", strawberry.lazy("race.types.race")]]
    associations: List[str]
    found_associations: List[
        Annotated["Association", strawberry.lazy("association.types")]
    ]
    items: List[str]
    found_items: List[Annotated["Item", strawberry.lazy("item.types.item")]]
    found_artifacts: List[Annotated["Artifact", strawberry.lazy("item.types.artifact")]]


@strawberry_django.type(models.GameLog)
class GameLog(Lockable, relay.Node):
    url: auto
    title: auto
    google_id: auto
    game_date: auto
    brief: auto
    synopsis: auto
    summary: auto
    places_set_in: ListConnectionWithTotalCount[
        Annotated["Place", strawberry.lazy("place.types.place")]
    ] = strawberry_django.connection()
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = strawberry.field(resolver=locked_by_self)

    artifacts: ListConnectionWithTotalCount[
        Annotated["Artifact", strawberry.lazy("item.types.artifact")]
    ] = strawberry_django.connection()
    associations: ListConnectionWithTotalCount[
        Annotated["Association", strawberry.lazy("association.types")]
    ] = strawberry_django.connection()
    characters: ListConnectionWithTotalCount[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()
    items: ListConnectionWithTotalCount[
        Annotated["Item", strawberry.lazy("item.types.item")]
    ] = strawberry_django.connection()
    places: ListConnectionWithTotalCount[
        Annotated["Place", strawberry.lazy("place.types.place")]
    ] = strawberry_django.connection()
    races: ListConnectionWithTotalCount[
        Annotated["Race", strawberry.lazy("race.types.race")]
    ] = strawberry_django.connection()
    ai_suggestions: Optional[CombinedGameLogAiSummary] = strawberry.field(
        resolver=lambda root, info: models.CombinedAiLogSuggestion(root)
    )


@strawberry_django.input(models.GameLog)
class GetOrCreateGameLogInput:
    url: auto
    lock: bool = False


@strawberry.input
class AddEntityLogInput:
    entity_id: strawberry.relay.GlobalID
    log_url: Optional[str] = strawberry.UNSET
    log_id: Optional[strawberry.relay.GlobalID] = strawberry.UNSET


@strawberry_django.partial(models.GameLog)
class GameLogInputPartial(strawberry_django.NodeInput):
    title: auto
    game_date: auto
    brief: auto
    synopsis: auto
    summary: auto
    places_set_in: auto
    artifacts: auto
    associations: auto
    characters: auto
    items: auto
    places: auto
    races: auto


@strawberry.input
class RemoveEntityLogInput:
    entity_id: strawberry.relay.GlobalID
    log_id: strawberry.relay.GlobalID


@strawberry_django.order_type(models.GameLog)
class GameLogOrder:
    game_date: auto


@strawberry.type
class GameLogQuery:
    game_logs: ListConnectionWithTotalCount[GameLog] = strawberry_django.connection(
        order=GameLogOrder
    )

    @strawberry.field(permission_classes=[IsSuperuser])
    def ai_log_suggestions(
        self, info, id: strawberry.relay.GlobalID
    ) -> GameLogAiSummary:
        gamelog = id.resolve_node_sync(info, ensure_type=models.GameLog)
        aiLogSummary = gamelog.get_ai_log_suggestions()
        return aiLogSummary

    @strawberry.field(permission_classes=[IsStaff])
    def consolidated_ai_log_suggestions(
        self, info, id: strawberry.relay.GlobalID
    ) -> CombinedGameLogAiSummary:
        from ..models import CombinedAiLogSuggestion

        gamelog = id.resolve_node_sync(info, ensure_type=models.GameLog)
        return CombinedAiLogSuggestion(gamelog)


@strawberry.type
class GameLogMutation:
    @strawberry_django.mutation(permission_classes=[IsStaff])
    def get_or_create_game_log(self, info, input: GetOrCreateGameLogInput) -> GameLog:
        google_id = models.GameLog.get_id_from_url(input.url)
        log = models.GameLog.objects.get_or_create(google_id=google_id)[0]
        if input.lock:
            log.lock(info.context.request.user)
        return log

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_gamelog(
        self,
        info,
        input: GameLogInputPartial,
    ) -> GameLog:
        data = vars(input)
        node_id = data.pop("id")
        gameLog: models.GameLog = node_id.resolve_node_sync(
            info, ensure_type=models.GameLog
        )
        resolvers.update(info, gameLog, resolvers.parse_input(info, data))
        gameLog.release_lock(info.context.request.user)
        return gameLog

    delete_game_log: GameLog = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def gamelog_lock(
        self,
        info,
        id: strawberry.relay.GlobalID,
    ) -> GameLog:
        gamelog = id.resolve_node_sync(info, ensure_type=models.GameLog)
        gamelog = gamelog.lock(info.context.request.user)
        return gamelog

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def gamelog_release_lock(self, info, id: strawberry.relay.GlobalID) -> GameLog:
        gamelog = id.resolve_node_sync(info, ensure_type=models.GameLog)
        gamelog = gamelog.release_lock(info.context.request.user)
        return gamelog

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def add_ai_log_suggestion(
        self,
        info,
        id: strawberry.relay.GlobalID,
        title: str,
        brief: str,
        synopsis: Optional[str],
        associations: List[str],
        characters: List[str],
        items: List[str],
        places: List[str],
        races: List[str],
    ) -> GameLog:
        gamelog = id.resolve_node_sync(info, ensure_type=models.GameLog)
        gamelog.ailogsuggestion_set.create(
            title=title,
            brief=brief,
            synopsis=synopsis,
            associations=associations,
            characters=characters,
            items=items,
            places=places,
            races=races,
        )
        return gamelog
