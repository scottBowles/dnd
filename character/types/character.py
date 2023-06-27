from typing import TYPE_CHECKING, Annotated, Iterable, Optional
from nucleus.permissions import IsLockUserOrSuperuserIfLocked, IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, EntityInputPartial
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto
from strawberry_django_plus.mutations import resolvers

from .. import models
from .feature import Feature
from .proficiency import Proficiency
from race.types import Race

if TYPE_CHECKING:
    from character.types.character import Character
    from item.types import Artifact, Item
    from association.types import Association
    from place.types.place import Place
    from race.types.race import Race


@gql.django.type(models.Character)
class Character(Entity, relay.Node):
    size: auto
    race: Optional[Race]
    features_and_traits: relay.Connection[Feature] = gql.django.connection()
    proficiencies: relay.Connection[Proficiency] = gql.django.connection()
    associations: relay.Connection[
        Annotated["Association", gql.lazy("association.types")]
    ] = gql.django.connection()
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


@gql.django.input(models.Character)
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


@gql.django.partial(models.Character)
class CharacterInputPartial(EntityInputPartial, gql.NodeInput):
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


@gql.type
class CharacterQuery:
    character: Optional[Character] = gql.django.field()
    characters: relay.Connection[Character] = gql.django.connection()

    @gql.django.connection
    def Characters_connection_filtered(
        self, name_startswith: str
    ) -> Iterable[Character]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Character.objects.filter(name__startswith=name_startswith)


@gql.type
class CharacterMutation:
    create_character: Character = gql.django.create_mutation(
        CharacterInput, permission_classes=[IsStaff]
    )

    @gql.django.mutation(permission_classes=[IsStaff, IsLockUserOrSuperuserIfLocked])
    def update_character(
        self,
        info,
        input: CharacterInputPartial,
    ) -> Character:
        data = vars(input)
        node_id = data.pop("id")
        character: models.Character = node_id.resolve_node(
            info, ensure_type=models.Character
        )
        resolvers.update(info, character, resolvers.parse_input(info, data))
        character.release_lock(info.context.request.user)
        return character

    delete_character: Character = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser, IsLockUserOrSuperuserIfLocked]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def character_add_image(
        self, info, id: gql.relay.GlobalID, image_id: str
    ) -> Character:
        obj = id.resolve_node(info)
        obj.image_ids = obj.image_ids + [image_id]
        obj.save()
        return obj

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def character_lock(self, info, id: gql.relay.GlobalID) -> Character:
        character = id.resolve_node(info)
        character = character.lock(info.context.request.user)
        return character

    @gql.django.input_mutation(permission_classes=[IsLockUserOrSuperuserIfLocked])
    def character_release_lock(self, info, id: gql.relay.GlobalID) -> Character:
        character = id.resolve_node(info)
        character = character.release_lock(info.context.request.user)
        return character
