from typing import TYPE_CHECKING, Annotated, Iterable

import strawberry
import strawberry_django
from strawberry import auto, relay

from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection

from .. import models

if TYPE_CHECKING:
    from character.types.character import Character


@strawberry_django.type(models.Feature)
class Feature(relay.Node):
    name: auto
    description: auto
    characters: DjangoListConnection[
        Annotated["Character", strawberry.lazy("character.types.character")]
    ] = strawberry_django.connection()


@strawberry_django.input(models.Feature)
class FeatureInput:
    name: auto
    description: auto
    characters: auto


@strawberry_django.partial(models.Feature)
class FeatureInputPartial(strawberry_django.NodeInput):
    name: auto
    description: auto
    characters: auto


@strawberry.type
class FeatureQuery:
    features: DjangoListConnection[Feature] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Feature])
    # def features_connection_filtered(self, name_startswith: str) -> Iterable[Feature]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Feature.objects.filter(name__startswith=name_startswith)


@strawberry.type
class FeatureMutation:
    create_feature: Feature = strawberry_django.mutations.create(
        FeatureInput, permission_classes=[IsStaff]
    )
    update_feature: Feature = strawberry_django.mutations.update(
        FeatureInputPartial, permission_classes=[IsStaff]
    )
    delete_feature: Feature = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
