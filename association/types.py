from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from association import models
from strawberry_django_plus import gql
from strawberry_django_plus.mutations import resolvers
from strawberry_django_plus.gql import relay, auto
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, EntityInputPartial

if TYPE_CHECKING:
    from character.types.character import Character
    from association.types import Association


@gql.django.type(models.Association)
class Association(Entity, relay.Node):
    characters: relay.Connection[
        Annotated["Character", gql.lazy("character.types.character")]
    ] = gql.django.connection()


@gql.django.input(models.Association)
class AssociationInput(EntityInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@gql.django.partial(models.Association)
class AssociationInputPartial(EntityInputPartial, gql.NodeInput):
    characters: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@gql.type
class AssociationQuery:
    association: Optional[Association] = gql.django.field()
    associations: relay.Connection[Association] = gql.django.connection()

    @gql.django.connection
    def associations_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[Association]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Association.objects.filter(name__startswith=name_startswith)


@gql.type
class AssociationMutation:
    create_association: Association = gql.django.create_mutation(
        AssociationInput,
        permission_classes=[IsStaff],
    )

    @gql.django.mutation(permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked])
    def update_association(
        self,
        info,
        input: AssociationInputPartial,
    ) -> Association:
        data = vars(input)
        node_id = data.pop("id")
        association: models.Association = node_id.resolve_node(
            info, ensure_type=models.Association
        )
        resolvers.update(info, association, resolvers.parse_input(info, data))
        association.release_lock(info.context.request.user)
        return association

    delete_association: Association = gql.django.delete_mutation(
        gql.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def association_add_image(
        self, info, id: gql.relay.GlobalID, image_id: str
    ) -> Association:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def association_lock(
        self,
        info,
        id: gql.relay.GlobalID,
    ) -> Association:
        association = id.resolve_node(info)
        association = association.lock(info.context.request.user)
        return association

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def association_release_lock(self, info, id: gql.relay.GlobalID) -> Association:
        association = id.resolve_node(info)
        association = association.release_lock(info.context.request.user)
        return association
