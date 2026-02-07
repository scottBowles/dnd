from typing import TYPE_CHECKING, Annotated, Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection
from nucleus.types import Entity, EntityInput, EntityInputPartial

from .. import models

if TYPE_CHECKING:
    from character.types.character import Character
    from race.types.race import Race


@strawberry_django.type(models.Race)
class Race(Entity, relay.Node):
    characters: DjangoListConnection[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()


@strawberry_django.input(models.Race)
class RaceInput(EntityInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry_django.partial(models.Race)
class RaceInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry.type
class RaceQuery:
    races: DjangoListConnection[Race] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Race])
    # def races_connection_filtered(self, name_startswith: str) -> Iterable[Race]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Race.objects.filter(name__startswith=name_startswith)


@strawberry.type
class RaceMutation:
    create_race: Race = strawberry_django.mutations.create(
        RaceInput, permission_classes=[IsStaff]
    )

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_race(
        self,
        info,
        input: RaceInputPartial,
    ) -> Race:
        data = vars(input)
        node_id = data.pop("id")
        race: models.Race = node_id.resolve_node_sync(info, ensure_type=models.Race)
        resolvers.update(info, race, resolvers.parse_input(info, data))
        race.release_lock(info.context.request.user)
        return race

    delete_race: Race = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def race_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Race:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def race_lock(self, info, id: strawberry.relay.GlobalID) -> Race:
        race = id.resolve_node_sync(info)
        race = race.lock(info.context.request.user)
        return race

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def race_release_lock(self, info, id: strawberry.relay.GlobalID) -> Race:
        race = id.resolve_node_sync(info)
        race = race.release_lock(info.context.request.user)
        return race
