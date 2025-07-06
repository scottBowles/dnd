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
    from item.types import Artifact, Item


@strawberry_django.type(models.Artifact)
class Artifact(Entity, relay.Node):
    items: DjangoListConnection[Annotated["Item", strawberry.lazy("item.types")]] = (
        strawberry_django.connection()
    )
    notes: auto


@strawberry_django.input(models.Artifact)
class ArtifactInput(EntityInput):
    items: auto
    notes: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry_django.partial(models.Artifact)
class ArtifactInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    items: auto
    notes: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry.type
class ArtifactQuery:
    artifacts: DjangoListConnection[Artifact] = strawberry_django.connection()

    @strawberry_django.connection(DjangoListConnection[Artifact])
    def Artifacts_connection_filtered(self, name_startswith: str) -> Iterable[Artifact]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Artifact.objects.filter(name__startswith=name_startswith)


@strawberry.type
class ArtifactMutation:
    create_artifact: Artifact = strawberry_django.mutations.create(
        ArtifactInput, permission_classes=[IsStaff]
    )

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_artifact(
        self,
        info,
        input: ArtifactInputPartial,
    ) -> Artifact:
        data = vars(input)
        node_id = data.pop("id")
        artifact: models.Artifact = node_id.resolve_node_sync(
            info, ensure_type=models.Artifact
        )
        resolvers.update(info, artifact, resolvers.parse_input(info, data))
        artifact.release_lock(info.context.request.user)
        return artifact

    delete_artifact: Artifact = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def artifact_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Artifact:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def artifact_lock(self, info, id: strawberry.relay.GlobalID) -> Artifact:
        artifact = id.resolve_node_sync(info)
        artifact = artifact.lock(info.context.request.user)
        return artifact

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def artifact_release_lock(self, info, id: strawberry.relay.GlobalID) -> Artifact:
        artifact = id.resolve_node_sync(info)
        artifact = artifact.release_lock(info.context.request.user)
        return artifact
