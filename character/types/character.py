from typing import TYPE_CHECKING, Annotated, Iterable, Optional

import strawberry
import strawberry_django
from strawberry import auto, relay
from strawberry_django.mutations import resolvers

from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection
from nucleus.types import Entity, EntityInput, EntityInputPartial
from race.types import Race

from .. import models
from .feature import Feature
from .proficiency import Proficiency

if TYPE_CHECKING:
    from association.types import Association
    from character.types.character import Character
    from race.types.race import Race


@strawberry_django.type(models.Character)
class Character(Entity, relay.Node):
    size: auto
    race: Optional[Race]
    features_and_traits: DjangoListConnection[Feature] = strawberry_django.connection()
    proficiencies: DjangoListConnection[Proficiency] = strawberry_django.connection()
    associations: DjangoListConnection[
        Annotated["Association", strawberry.lazy("association.types")]
    ] = strawberry_django.connection()


@strawberry_django.input(models.Character)
class CharacterInput(EntityInput):
    size: auto
    race: auto
    features_and_traits: auto
    proficiencies: auto
    associations: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry_django.partial(models.Character)
class CharacterInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    size: auto
    race: auto
    features_and_traits: auto
    proficiencies: auto
    associations: auto
    related_artifacts: auto
    related_associations: auto
    related_characters: auto
    related_items: auto
    related_places: auto
    related_races: auto


@strawberry.type
class CharacterQuery:
    characters: DjangoListConnection[Character] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Character])
    # def characters_connection_filtered(
    #     self, name_startswith: str
    # ) -> Iterable[Character]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Character.objects.filter(name__startswith=name_startswith)


@strawberry.type
class CharacterMutation:
    create_character: Character = strawberry_django.mutations.create(
        CharacterInput, permission_classes=[IsStaff]
    )

    @strawberry_django.mutation(
        permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked]
    )
    def update_character(
        self,
        info,
        input: CharacterInputPartial,
    ) -> Character:
        data = vars(input)
        node_id = data.pop("id")
        character: models.Character = node_id.resolve_node_sync(
            info, ensure_type=models.Character
        )
        resolvers.update(info, character, resolvers.parse_input(info, data))
        character.release_lock(info.context.request.user)
        return character

    delete_character: Character = strawberry_django.mutations.delete(
        strawberry_django.NodeInput,
        permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked],
    )

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def character_add_image(
        self, info, id: strawberry.relay.GlobalID, image_id: str
    ) -> Character:
        obj = id.resolve_node_sync(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @strawberry_django.input_mutation(permission_classes=[IsStaff])
    def character_lock(self, info, id: strawberry.relay.GlobalID) -> Character:
        character = id.resolve_node_sync(info)
        character = character.lock(info.context.request.user)
        return character

    @strawberry_django.input_mutation(
        permission_classes=[IsLockUserOrSuperuserIfLocked]
    )
    def character_release_lock(self, info, id: strawberry.relay.GlobalID) -> Character:
        character = id.resolve_node_sync(info)
        character = character.release_lock(info.context.request.user)
        return character
