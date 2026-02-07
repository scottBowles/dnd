from typing import Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models


@strawberry_django.type(models.Trait)
class Trait(relay.Node):
    name: auto
    description: auto


@strawberry_django.input(models.Trait)
class TraitInput:
    name: auto
    description: auto


@strawberry_django.partial(models.Trait)
class TraitInputPartial(strawberry_django.NodeInput):
    name: auto
    description: auto


@strawberry.type
class TraitQuery:
    traits: DjangoListConnection[Trait] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Trait])
    # def traits_connection_filtered(self, name_startswith: str) -> Iterable[Trait]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Trait.objects.filter(name__startswith=name_startswith)


@strawberry.type
class TraitMutation:
    create_trait: Trait = strawberry_django.mutations.create(
        TraitInput, permission_classes=[IsStaff]
    )
    update_trait: Trait = strawberry_django.mutations.update(
        TraitInputPartial, permission_classes=[IsStaff]
    )
    delete_trait: Trait = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
