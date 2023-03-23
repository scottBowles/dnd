from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from association import models
from nucleus.types import Entity, EntityInput, GameLog, User
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto
from nucleus.permissions import IsStaff, IsSuperuser

if TYPE_CHECKING:
    from character.types.npc import Npc


@gql.django.type(models.Association)
class Association(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    npcs: relay.Connection[
        Annotated["Npc", gql.lazy("character.types.npc")]
    ] = gql.django.connection()


@gql.django.input(models.Association)
class AssociationInput(EntityInput):
    npcs: auto


@gql.django.partial(models.Association)
class AssociationInputPartial(EntityInput, gql.NodeInput):
    npcs: auto


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
    update_association: Association = gql.django.update_mutation(
        AssociationInputPartial,
        permission_classes=[IsStaff],
    )
    delete_association: Association = gql.django.delete_mutation(
        gql.NodeInput,
        permission_classes=[IsSuperuser],
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def association_lock(
        self,
        info,
        id: gql.relay.GlobalID,
    ) -> Association:
        association = id.resolve_node(info)
        association = association.lock(info.context.request.user)
        return association

    @gql.django.input_mutation(permission_classes=[IsSuperuser])
    def association_release_lock(self, info, id: gql.relay.GlobalID) -> Association:
        association = id.resolve_node(info)
        association = association.release_lock(info.context.request.user)
        return association