from typing import TYPE_CHECKING, Annotated, List, Optional
from nucleus import models
from nucleus.permissions import IsStaff
from strawberry.types import Info
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay
import datetime
from .user import User

if TYPE_CHECKING:
    from nucleus.types.gamelog import GameLog, AddEntityLogInput, RemoveEntityLogInput
    from character.types.character import Character
    from item.types import Artifact, Item
    from association.types import Association
    from place.types.place import Place
    from race.types.race import Race


def locked_by_self(root, info: Info) -> bool:
    """
    Add this as a resolver on any type that has a lock_user field like this:

    locked_by_self: bool = gql.field(resolver=locked_by_self)
    """
    return root.lock_user == info.context.request.user


@gql.django.type(models.Alias)
class Alias(relay.Node):
    name: str
    is_primary: bool


@gql.interface
class Lockable:
    id: gql.relay.GlobalID
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = gql.field(resolver=locked_by_self)


@gql.interface
class Entity(Lockable):
    id: gql.relay.GlobalID
    name: str
    description: Optional[str]
    markdown_notes: Optional[str]
    image_ids: List[str]
    thumbnail_id: Optional[str]
    created: datetime.datetime
    updated: datetime.datetime
    logs: relay.Connection[
        Annotated["GameLog", gql.lazy("nucleus.types.gamelog")]
    ] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: Optional[datetime.datetime]
    locked_by_self: bool = gql.field(resolver=locked_by_self)
    aliases: relay.Connection[Alias] = gql.django.connection()
    related_artifacts: relay.Connection[
        Annotated["Artifact", gql.lazy("item.types.artifact")]
    ] = gql.django.connection()
    related_associations: relay.Connection[
        Annotated["Association", gql.lazy("association.types")]
    ] = gql.django.connection()
    related_characters: relay.Connection[
        Annotated["Character", gql.lazy("character.types.character")]
    ] = gql.django.connection()
    related_items: relay.Connection[
        Annotated["Item", gql.lazy("item.types.item")]
    ] = gql.django.connection()
    related_places: relay.Connection[
        Annotated["Place", gql.lazy("place.types.place")]
    ] = gql.django.connection()
    related_races: relay.Connection[
        Annotated["Race", gql.lazy("race.types.race")]
    ] = gql.django.connection()


class EntityInput:
    name: str
    markdown_notes: Optional[str]
    image_ids: Optional[List[str]]
    thumbnail_id: Optional[str]
    description: Optional[str]
    logs: Optional[List[gql.relay.GlobalID]]
    # `auto` fields won't work via mixins, so they need to be added manually
    # related_artifacts: auto
    # related_associations: auto
    # related_characters: auto
    # related_items: auto
    # related_places: auto
    # related_races: auto


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


@gql.input
class EntityAddImageInput:
    id: gql.relay.GlobalID
    image_id: str


@gql.input
class EntityAddAliasInput:
    id: gql.relay.GlobalID
    alias: str


@gql.type
class NodeQuery:
    @gql.field
    def node(self, info, id: gql.relay.GlobalID) -> Optional[relay.Node]:
        return id.resolve_node(info)


@gql.type
class EntityMutation:
    @gql.mutation(permission_classes=[IsStaff])
    def add_entity_log(
        self,
        info,
        input: Annotated["AddEntityLogInput", gql.lazy("nucleus.types.gamelog")],
    ) -> relay.Node:
        entity = input.entity_id.resolve_node(info)

        if input.log_id is not gql.UNSET:
            log = input.log_id.resolve_node(info)
        else:
            google_id = models.GameLog.get_id_from_url(input.log_url)
            log = models.GameLog.objects.get_or_create(google_id=google_id)[0]

        entity.logs.add(log)
        entity.save()
        return entity

    @gql.mutation(permission_classes=[IsStaff])
    def remove_entity_log(
        self,
        info,
        input: Annotated["RemoveEntityLogInput", gql.lazy("nucleus.types.gamelog")],
    ) -> relay.Node:
        log = input.log_id.resolve_node(info)
        entity = input.entity_id.resolve_node(info)
        entity.logs.remove(log)
        entity.save()
        return entity

    @gql.mutation(permission_classes=[IsStaff])
    def entity_add_image(self, info, input: EntityAddImageInput) -> relay.Node:
        obj = input.id.resolve_node(info)
        obj.image_ids = obj.image_ids + [input.image_id]
        obj.save()
        return obj

    @gql.mutation(permission_classes=[IsStaff])
    def entity_add_alias(self, info, input: EntityAddAliasInput) -> relay.Node:
        obj = input.id.resolve_node(info)
        try:
            obj.aliases.get(name=input.alias)
            return obj
        except models.Alias.DoesNotExist:
            obj.aliases.create(name=input.alias)
            obj.save()
            return obj

    @gql.mutation(permission_classes=[IsStaff])
    def lock(self, info, input: gql.NodeInput) -> Lockable:
        obj = input.id.resolve_node(info)
        obj.lock(info.context.request.user)
        return obj

    @gql.mutation(permission_classes=[IsStaff])
    def unlock(self, info, input: gql.NodeInput) -> Lockable:
        obj = input.id.resolve_node(info)
        obj.release_lock(info.context.request.user)
        return obj
