from typing import Iterable, Optional
from nucleus.permissions import IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, GameLog, User
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models
from .feature import Feature
from .proficiency import Proficiency
from association.types import Association
from race.types import Race


@gql.django.type(models.NPC)
class Npc(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    size: auto
    race: Optional[Race]
    features_and_traits: relay.Connection[Feature] = gql.django.connection()
    proficiencies: relay.Connection[Proficiency] = gql.django.connection()
    associations: relay.Connection[Association] = gql.django.connection()


@gql.django.input(models.NPC)
class NpcInput(EntityInput):
    size: auto
    race: auto
    features_and_traits: auto
    proficiencies: auto
    associations: auto


@gql.django.partial(models.NPC)
class NpcInputPartial(EntityInput, gql.NodeInput):
    size: auto
    race: auto
    features_and_traits: auto
    proficiencies: auto
    associations: auto


@gql.type
class NpcQuery:
    npc: Optional[Npc] = gql.django.field()
    npcs: relay.Connection[Npc] = gql.django.connection()

    @gql.django.connection
    def Npcs_connection_filtered(self, name_startswith: str) -> Iterable[Npc]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.NPC.objects.filter(name__startswith=name_startswith)


@gql.type
class NpcMutation:
    create_npc: Npc = gql.django.create_mutation(NpcInput, permission_classes=[IsStaff])
    update_npc: Npc = gql.django.update_mutation(
        NpcInputPartial, permission_classes=[IsStaff]
    )
    delete_npc: Npc = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )

    @gql.django.input_mutation(permission_classes=[IsStaff])
    def npc_lock(self, info, id: gql.relay.GlobalID) -> Npc:
        npc = id.resolve_node(info)
        npc = npc.lock(info.context.request.user)
        return npc

    @gql.django.input_mutation(permission_classes=[IsSuperuser])
    def npc_release_lock(self, info, id: gql.relay.GlobalID) -> Npc:
        npc = id.resolve_node(info)
        npc = npc.release_lock(info.context.request.user)
        return npc
