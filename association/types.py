from typing import TYPE_CHECKING, Annotated, Iterable, Optional

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from association import models
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, EntityInputPartial
from nucleus.relay import ListConnectionWithTotalCount

if TYPE_CHECKING:
    from association.types import Association
    from character.types.character import Character


@strawberry_django.type(models.Association)
class Association(Entity, relay.Node):
    characters: ListConnectionWithTotalCount[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()


@strawberry_django.input(models.Association)
class AssociationInput(EntityInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry_django.partial(models.Association)
class AssociationInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry.type
class AssociationQuery:
    associations: ListConnectionWithTotalCount[Association] = (
        strawberry_django.connection()
    )

    @strawberry_django.connection(ListConnectionWithTotalCount[Association])
    def associations_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[Association]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Association.objects.filter(name__startswith=name_startswith)


@strawberry.type
class AssociationMutation:
    create_association: Association = strawberry_django.mutations.create(
        AssociationInput,
        permission_classes=[IsStaff],
    )

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_association(
        self,
        info,
        input: AssociationInputPartial,
    ) -> Association:
        data = vars(input)
        node_id = data.pop("id")
        association: models.Association = node_id.resolve_node_sync(
            info, ensure_type=models.Association
        )
        resolvers.update(info, association, resolvers.parse_input(info, data))
        association.release_lock(info.context.request.user)
        return association

    delete_association: Association = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def association_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Association:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def association_lock(
        self,
        info,
        id: strawberry.relay.GlobalID,
    ) -> Association:
        association = id.resolve_node_sync(info)
        association = association.lock(info.context.request.user)
        return association

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def association_release_lock(
        self, info, id: strawberry.relay.GlobalID
    ) -> Association:
        association = id.resolve_node_sync(info)
        association = association.release_lock(info.context.request.user)
        return association
