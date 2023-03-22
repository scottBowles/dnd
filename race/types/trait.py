from typing import Iterable, Optional
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from .. import models


@gql.django.type(models.Trait)
class Trait(relay.Node):
    name: auto
    description: auto


@gql.django.input(models.Trait)
class TraitInput:
    name: auto
    description: auto


@gql.django.partial(models.Trait)
class TraitInputPartial(gql.NodeInput):
    name: auto
    description: auto


@gql.type
class TraitQuery:
    trait: Optional[Trait] = gql.django.field()
    traits: relay.Connection[Trait] = gql.django.connection()

    @gql.django.connection
    def Traits_connection_filtered(self, name_startswith: str) -> Iterable[Trait]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Trait.objects.filter(name__startswith=name_startswith)


@gql.type
class TraitMutation:
    create_trait: Trait = gql.django.create_mutation(TraitInput)
    update_trait: Trait = gql.django.update_mutation(TraitInputPartial)
    delete_trait: Trait = gql.django.delete_mutation(gql.NodeInput)
