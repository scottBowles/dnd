from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from nucleus.permissions import IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, GameLog, User
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto
from django.utils import timezone

from .. import models

if TYPE_CHECKING:
    from item.types import Item


@gql.django.type(models.Artifact)
class Artifact(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    items: relay.Connection[
        Annotated["Item", gql.lazy("item.types")]
    ] = gql.django.connection()
    notes: auto


@gql.django.input(models.Artifact)
class ArtifactInput(EntityInput):
    logs: auto
    items: auto
    notes: auto


@gql.django.partial(models.Artifact)
class ArtifactInputPartial(EntityInput, gql.NodeInput):
    logs: auto
    items: auto
    notes: auto


@gql.type
class ArtifactQuery:
    artifact: Optional[Artifact] = gql.django.field()
    artifacts: relay.Connection[Artifact] = gql.django.connection()

    @gql.django.connection
    def Artifacts_connection_filtered(self, name_startswith: str) -> Iterable[Artifact]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Artifact.objects.filter(name__startswith=name_startswith)


@gql.type
class ArtifactMutation:
    create_artifact: Artifact = gql.django.create_mutation(
        ArtifactInput, permission_classes=[IsStaff]
    )
    update_artifact: Artifact = gql.django.update_mutation(
        ArtifactInputPartial, permission_classes=[IsStaff]
    )
    delete_artifact: Artifact = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def artifact_add_image(
        self, info, id: gql.relay.GlobalID, image_id: str
    ) -> Artifact:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def artifact_lock(self, info, id: gql.relay.GlobalID) -> Artifact:
        artifact = id.resolve_node(info)
        artifact = artifact.lock(info.context.request.user)
        return artifact

    @gql.django.input_mutation(permission_classes=[IsSuperuser])
    def artifact_release_lock(self, info, id: gql.relay.GlobalID) -> Artifact:
        artifact = id.resolve_node(info)
        artifact = artifact.release_lock(info.context.request.user)
        return artifact