from typing import Annotated, Iterable, Optional, TYPE_CHECKING
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from nucleus.permissions import IsStaff, IsSuperuser

from .. import models

if TYPE_CHECKING:
    from character.types.character import Character


@gql.django.type(models.Feature)
class Feature(relay.Node):
    name: auto
    description: auto
    characters: relay.Connection[
        Annotated["Character", gql.lazy("character.types.character")]
    ] = gql.django.connection()


@gql.django.input(models.Feature)
class FeatureInput:
    name: auto
    description: auto
    characters: auto


@gql.django.partial(models.Feature)
class FeatureInputPartial(gql.NodeInput):
    name: auto
    description: auto
    characters: auto


@gql.type
class FeatureQuery:
    feature: Optional[Feature] = gql.django.field()
    features: relay.Connection[Feature] = gql.django.connection()

    @gql.django.connection
    def Features_connection_filtered(self, name_startswith: str) -> Iterable[Feature]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Feature.objects.filter(name__startswith=name_startswith)


@gql.type
class FeatureMutation:
    create_feature: Feature = gql.django.create_mutation(
        FeatureInput, permission_classes=[IsStaff]
    )
    update_feature: Feature = gql.django.update_mutation(
        FeatureInputPartial, permission_classes=[IsStaff]
    )
    delete_feature: Feature = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )
