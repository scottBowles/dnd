import datetime
from typing import TYPE_CHECKING, Annotated, List, Optional

import strawberry
import strawberry_django
from strawberry.types import Info
from strawberry import relay

from nucleus import models
from nucleus.permissions import IsStaff
from strawberry_django.relay import DjangoListConnection

from .user import User

if TYPE_CHECKING:
    from association.types import Association
    from character.types.character import Character
    from item.types import Artifact, Item
    from nucleus.types.gamelog import AddEntityLogInput, GameLog, RemoveEntityLogInput
    from place.types.place import Place
    from race.types.race import Race


def locked_by_self(root, info: Info) -> bool:
    """
    Add this as a resolver on any type that has a lock_user field like this:

    locked_by_self: bool = strawberry.field(resolver=locked_by_self)
    """
    return root.lock_user == info.context.request.user


@strawberry_django.type(models.Alias)
class Alias(relay.Node):
    name: str
    is_primary: bool


@strawberry.interface
class Lockable:
    id: strawberry.relay.GlobalID
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = strawberry.field(resolver=locked_by_self)


@strawberry.interface
class Entity(Lockable):
    id: strawberry.relay.GlobalID
    name: str
    description: Optional[str]
    markdown_notes: Optional[str]
    image_ids: List[str]
    thumbnail_id: Optional[str]
    created: datetime.datetime
    updated: datetime.datetime
    logs: DjangoListConnection[
        Annotated["GameLog", strawberry.lazy("nucleus.types.gamelog")]
    ] = strawberry_django.connection()
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = strawberry.field(resolver=locked_by_self)
    aliases: DjangoListConnection[Alias] = strawberry_django.connection()
    related_artifacts: DjangoListConnection[
        Annotated["Artifact", strawberry.lazy("item.types.artifact")]
    ] = strawberry_django.connection()
    related_associations: DjangoListConnection[
        Annotated["Association", strawberry.lazy("association.types")]
    ] = strawberry_django.connection()
    related_characters: DjangoListConnection[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()
    related_items: DjangoListConnection[
        Annotated["Item", strawberry.lazy("item.types.item")]
    ] = strawberry_django.connection()
    related_places: DjangoListConnection[
        Annotated["Place", strawberry.lazy("place.types.place")]
    ] = strawberry_django.connection()
    related_races: DjangoListConnection[
        Annotated["Race", strawberry.lazy("race.types.race")]
    ] = strawberry_django.connection()


@strawberry.input
class EntityInput:
    name: str
    markdown_notes: Optional[str]
    image_ids: Optional[List[str]]
    thumbnail_id: Optional[str]
    description: Optional[str]
    logs: Optional[List[strawberry.relay.GlobalID]]
    # `auto` fields won't work via mixins, so they need to be added manually
    # related_artifacts: auto
    # related_associations: auto
    # related_characters: auto
    # related_items: auto
    # related_places: auto
    # related_races: auto


@strawberry.input
class EntityInputPartial:
    name: Optional[str]
    markdown_notes: Optional[str]
    image_ids: Optional[List[str]]
    thumbnail_id: Optional[str]
    description: Optional[str]
    # logs: Optional[List[GameLogInput]]
    # `auto` fields won't work via mixins, so they need to be added manually
    # related_artifacts: auto
    # related_associations: auto
    # related_characters: auto
    # related_items: auto
    # related_places: auto
    # related_races: auto


@strawberry.input
class EntityAddImageInput:
    id: strawberry.relay.GlobalID
    image_id: str


@strawberry.input
class EntityAddAliasInput:
    id: strawberry.relay.GlobalID
    alias: str


@strawberry.type
class NodeQuery:
    node: relay.Node = relay.node()


@strawberry.type
class EntityMutation:
    @strawberry.mutation(permission_classes=[IsStaff])
    def add_entity_log(
        self,
        info,
        input: Annotated["AddEntityLogInput", strawberry.lazy("nucleus.types.gamelog")],
    ) -> relay.Node:
        entity = input.entity_id.resolve_node_sync(info)

        if input.log_id is not strawberry.UNSET:
            log = input.log_id.resolve_node_sync(info)
        else:
            google_id = models.GameLog.get_id_from_url(input.log_url)
            log = models.GameLog.objects.get_or_create(google_id=google_id)[0]

        entity.logs.add(log)
        entity.save()
        return entity

    @strawberry.mutation(permission_classes=[IsStaff])
    def remove_entity_log(
        self,
        info,
        input: Annotated[
            "RemoveEntityLogInput", strawberry.lazy("nucleus.types.gamelog")
        ],
    ) -> relay.Node:
        log = input.log_id.resolve_node_sync(info)
        entity = input.entity_id.resolve_node_sync(info)
        entity.logs.remove(log)
        entity.save()
        return entity

    @strawberry.mutation(permission_classes=[IsStaff])
    def entity_add_image(self, info, input: EntityAddImageInput) -> relay.Node:
        obj = input.id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [input.image_id]
        obj.save()
        return obj

    @strawberry.mutation(permission_classes=[IsStaff])
    def entity_add_alias(self, info, input: EntityAddAliasInput) -> relay.Node:
        obj = input.id.resolve_node_sync(info)
        try:
            obj.aliases.get(name=input.alias)
            return obj
        except models.Alias.DoesNotExist:
            obj.aliases.create(name=input.alias)
            obj.save()
            return obj

    @strawberry.mutation(permission_classes=[IsStaff])
    def lock(self, info, input: strawberry_django.NodeInput) -> Lockable:
        obj = input.id.resolve_node_sync(info)
        obj.lock(info.context.request.user)
        return obj

    @strawberry.mutation(permission_classes=[IsStaff])
    def unlock(self, info, input: strawberry_django.NodeInput) -> Lockable:
        obj = input.id.resolve_node_sync(info)
        obj.release_lock(info.context.request.user)
        return obj
