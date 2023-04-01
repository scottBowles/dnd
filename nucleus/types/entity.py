from typing import List, Optional
from strawberry_django_plus.gql import auto
from strawberry.types import Info


def locked_by_self(root, info: Info) -> bool:
    """
    Add this as a resolver on any type that has a lock_user field like this:

    locked_by_self: bool = gql.field(resolver=locked_by_self)
    """
    return root.lock_user == info.context.request.user


class Entity:
    """
    A base type for other entity types to inherit from
    The Entity model is abstract, so this type is not used directly

    Add `logs: List[GameLog]` to include logs. These cannot be added
    here because it needs to be associated with the specific entity type
    """

    markdown_notes: auto
    image_ids: List[str]
    thumbnail_id: auto
    name: auto
    description: auto
    created: auto
    updated: auto


class EntityInput:
    markdown_notes: auto
    image_ids: Optional[List[str]]
    thumbnail_id: auto
    name: auto
    description: auto
    logs: auto
