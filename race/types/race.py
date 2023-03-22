from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from nucleus.types import Entity, EntityInput, GameLog, User
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models

if TYPE_CHECKING:
    from character.types.npc import Npc


@gql.django.type(models.Race)
class Race(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    npcs: relay.Connection[
        Annotated["Npc", gql.lazy("character.types.npc")]
    ] = gql.django.connection()


@gql.django.input(models.Race)
class RaceInput(EntityInput):
    npcs: auto


@gql.django.partial(models.Race)
class RaceInputPartial(EntityInput, gql.NodeInput):
    npcs: auto


@gql.type
class RaceQuery:
    race: Optional[Race] = gql.django.field()
    races: relay.Connection[Race] = gql.django.connection()

    @gql.django.connection
    def Races_connection_filtered(self, name_startswith: str) -> Iterable[Race]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Race.objects.filter(name__startswith=name_startswith)


@gql.type
class RaceMutation:
    create_race: Race = gql.django.create_mutation(RaceInput)
    update_race: Race = gql.django.update_mutation(RaceInputPartial)
    delete_race: Race = gql.django.delete_mutation(gql.NodeInput)

    @gql.django.input_mutation
    def race_add_image(self, info, id: gql.relay.GlobalID, image_id: str) -> Race:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation
    def race_lock(self, info, race_id: gql.relay.GlobalID) -> Race:
        race = race_id.resolve_node(info)
        race = race.lock(info.context.user)
        return race

    @gql.django.input_mutation
    def race_release_lock(self, info, race_id: gql.relay.GlobalID) -> Race:
        race = race_id.resolve_node(info)
        race = race.release_lock(info.context.user)
        return race
