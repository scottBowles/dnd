from typing import Iterable, Optional
from association import models
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, EntityInputPartial
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto
from strawberry_django_plus.mutations import resolvers

from place import models


@gql.django.type(models.Place)
class Place(Entity, relay.Node):
    place_type: auto
    parent: auto
    population: auto
    exports: auto
    common_races: auto
    associations: auto


@gql.django.input(models.Place)
class PlaceInput(EntityInput):
    pass


@gql.django.partial(models.Place)
class PlaceInputPartial(EntityInputPartial, gql.NodeInput):
    pass


@gql.type
class PlaceQuery:
    place: Optional[Place] = gql.django.field()
    places: relay.Connection[Place] = gql.django.connection()

    @gql.django.connection
    def Places_connection_filtered(self, name_startswith: str) -> Iterable[Place]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Place.objects.filter(name__startswith=name_startswith)


@gql.type
class PlaceMutation:
    create_place: Place = gql.django.create_mutation(
        PlaceInput, permission_classes=[IsStaff]
    )

    @gql.django.mutation(permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked])
    def update_place(
        self,
        info,
        input: PlaceInputPartial,
    ) -> Place:
        data = vars(input)
        node_id = data.pop("id")
        place: models.Place = node_id.resolve_node(info, ensure_type=models.Place)
        resolvers.update(info, place, resolvers.parse_input(info, data))
        place.release_lock(info.context.request.user)
        return place

    delete_place: Place = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def place_add_image(self, info, id: gql.relay.GlobalID, image_id: str) -> Place:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def place_lock(self, info, id: gql.relay.GlobalID) -> Place:
        place = id.resolve_node(info)
        place = place.lock(info.context.request.user)
        return place

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def place_release_lock(self, info, id: gql.relay.GlobalID) -> Place:
        place = id.resolve_node(info)
        place = place.release_lock(info.context.request.user)
        return place
