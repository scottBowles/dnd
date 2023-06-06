import datetime
from typing import TYPE_CHECKING, Annotated, List, Optional

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types.entity import Lockable, locked_by_self
from nucleus.types.user import User
from .. import models
from strawberry_django_plus import gql
from strawberry_django_plus.mutations import resolvers
from strawberry_django_plus.gql import relay, auto

if TYPE_CHECKING:
    from association.types import Association
    from character.types.character import Character
    from place.types.place import Place
    from race.types.race import Race
    from item.types.artifact import Artifact
    from item.types.item import Item


@gql.type
class GameLogAiSummary:
    title: str
    brief: str
    synopsis: str
    places: List[str]
    found_places: List[Annotated["Place", gql.lazy("place.types.place")]]
    characters: List[str]
    found_characters: List[
        Annotated["Character", gql.lazy("character.types.character")]
    ]
    races: List[str]
    found_races: List[Annotated["Race", gql.lazy("race.types.race")]]
    associations: List[str]
    found_associations: List[Annotated["Association", gql.lazy("association.types")]]
    items: List[str]
    found_items: List[Annotated["Item", gql.lazy("item.types.item")]]
    artifacts: List[str]
    found_artifacts: List[Annotated["Artifact", gql.lazy("item.types.artifact")]]


@gql.type
class CombinedGameLogAiSummary:
    titles: List[str]
    briefs: List[str]
    synopses: List[str]
    places: List[str]
    found_places: List[Annotated["Place", gql.lazy("place.types.place")]]
    characters: List[str]
    found_characters: List[
        Annotated["Character", gql.lazy("character.types.character")]
    ]
    races: List[str]
    found_races: List[Annotated["Race", gql.lazy("race.types.race")]]
    associations: List[str]
    found_associations: List[Annotated["Association", gql.lazy("association.types")]]
    items: List[str]
    found_items: List[Annotated["Item", gql.lazy("item.types.item")]]
    found_artifacts: List[Annotated["Artifact", gql.lazy("item.types.artifact")]]


@gql.django.type(models.GameLog)
class GameLog(Lockable, relay.Node):
    url: auto
    title: auto
    google_id: auto
    game_date: auto
    brief: auto
    synopsis: auto
    summary: auto
    places_set_in: relay.Connection[
        Annotated["Place", gql.lazy("place.types.place")]
    ] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = gql.field(resolver=locked_by_self)

    artifacts: relay.Connection[
        Annotated["Artifact", gql.lazy("item.types.artifact")]
    ] = gql.django.connection()
    associations: relay.Connection[
        Annotated["Association", gql.lazy("association.types")]
    ] = gql.django.connection()
    characters: relay.Connection[
        Annotated["Character", gql.lazy("character.types.character")]
    ] = gql.django.connection()
    items: relay.Connection[
        Annotated["Item", gql.lazy("item.types.item")]
    ] = gql.django.connection()
    places: relay.Connection[
        Annotated["Place", gql.lazy("place.types.place")]
    ] = gql.django.connection()
    races: relay.Connection[
        Annotated["Race", gql.lazy("race.types.race")]
    ] = gql.django.connection()
    ai_suggestions: Optional[CombinedGameLogAiSummary] = gql.field(
        resolver=lambda root, info: models.CombinedAiLogSuggestion(root)
    )


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
    summary: auto
    places_set_in: auto
    artifacts: auto
    associations: auto
    characters: auto
    items: auto
    places: auto
    races: auto


@gql.input
class RemoveEntityLogInput:
    entity_id: gql.relay.GlobalID
    log_id: gql.relay.GlobalID


@gql.django.ordering.order(models.GameLog)
class GameLogOrder:
    game_date: auto


@gql.type
class GameLogQuery:
    game_log: Optional[GameLog] = gql.django.field()
    game_logs: relay.Connection[GameLog] = gql.django.connection(order=GameLogOrder)

    @gql.field(permission_classes=[IsSuperuser])
    def ai_log_suggestions(self, info, id: gql.relay.GlobalID) -> GameLogAiSummary:
        gamelog = id.resolve_node(info, ensure_type=models.GameLog)
        aiLogSummary = gamelog.get_ai_log_suggestions()
        return aiLogSummary

    @gql.field(permission_classes=[IsStaff])
    def consolidated_ai_log_suggestions(
        self, info, id: gql.relay.GlobalID
    ) -> CombinedGameLogAiSummary:
        from ..models import CombinedAiLogSuggestion

        gamelog = id.resolve_node(info, ensure_type=models.GameLog)
        return CombinedAiLogSuggestion(gamelog)


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
        gamelog = id.resolve_node(info, ensure_type=models.GameLog)
        gamelog = gamelog.lock(info.context.request.user)
        return gamelog

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def gamelog_release_lock(self, info, id: gql.relay.GlobalID) -> GameLog:
        gamelog = id.resolve_node(info, ensure_type=models.GameLog)
        gamelog = gamelog.release_lock(info.context.request.user)
        return gamelog

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def add_ai_log_suggestion(
        self,
        info,
        id: gql.relay.GlobalID,
        title: str,
        brief: str,
        synopsis: Optional[str],
        associations: List[str],
        characters: List[str],
        items: List[str],
        places: List[str],
        races: List[str],
    ) -> GameLog:
        gamelog = id.resolve_node(info, ensure_type=models.GameLog)
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
