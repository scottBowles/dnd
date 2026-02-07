from typing import TYPE_CHECKING, Iterable, Optional

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from association import models
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection
from nucleus.types import Entity, EntityInput, EntityInputPartial
from place import models

if TYPE_CHECKING:
    from place.types.place import Place


@strawberry_django.type(models.Place)
class Place(Entity, relay.Node):
    place_type: auto
    parent: Optional["Place"]
    population: auto
    exports: auto
    common_races: auto
    associations: auto
    children: DjangoListConnection["Place"] = strawberry_django.connection()


@strawberry_django.input(models.Place)
class PlaceInput(EntityInput):
    place_type: auto
    children: auto
    parent: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry_django.partial(models.Place)
class PlaceInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    place_type: auto
    children: auto
    parent: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry.type
class PlaceQuery:
    places: DjangoListConnection[Place] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Place])
    # def places_connection_filtered(self, name_startswith: str) -> Iterable[Place]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Place.objects.filter(name__startswith=name_startswith)


@strawberry.type
class PlaceMutation:
    create_place: Place = strawberry_django.mutations.create(
        PlaceInput, permission_classes=[IsStaff]
    )

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_place(
        self,
        info,
        input: PlaceInputPartial,
    ) -> Place:
        data = vars(input)
        node_id = data.pop("id")
        place: models.Place = node_id.resolve_node_sync(info, ensure_type=models.Place)
        resolvers.update(info, place, resolvers.parse_input(info, data))
        place.release_lock(info.context.request.user)
        return place

    delete_place: Place = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def place_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Place:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def place_lock(self, info, id: strawberry.relay.GlobalID) -> Place:
        place = id.resolve_node_sync(info)
        place = place.lock(info.context.request.user)
        return place

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def place_release_lock(self, info, id: strawberry.relay.GlobalID) -> Place:
        place = id.resolve_node_sync(info)
        place = place.release_lock(info.context.request.user)
        return place
