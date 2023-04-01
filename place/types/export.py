from typing import Iterable, Optional
from association import models
from nucleus.permissions import IsStaff, IsSuperuser
from nucleus.types import Entity, EntityInput, GameLog, User, locked_by_self
from strawberry_django_plus import gql
from strawberry_django_plus.gql import relay, auto

from place import models


@gql.django.type(models.Export)
class Export(Entity, relay.Node):
    logs: relay.Connection[GameLog] = gql.django.connection()
    lock_user: Optional[User]
    lock_time: auto
    locked_by_self: bool = gql.field(resolver=locked_by_self)


@gql.django.input(models.Export)
class ExportInput(EntityInput):
    pass


@gql.django.partial(models.Export)
class ExportInputPartial(EntityInput, gql.NodeInput):
    pass


@gql.type
class ExportQuery:
    export: Optional[Export] = gql.django.field()
    exports: relay.Connection[Export] = gql.django.connection()

    @gql.django.connection
    def Exports_connection_filtered(self, name_startswith: str) -> Iterable[Export]:
        # Note that this resolver is special. It should not resolve the connection, but
        # the iterable of nodes itself. Thus, any arguments defined here will be appended
        # to the query, and the pagination of the iterable returned here will be
        # automatically handled.
        return models.Export.objects.filter(name__startswith=name_startswith)


@gql.type
class ExportMutation:
    create_export: Export = gql.django.create_mutation(
        ExportInput, permission_classes=[IsStaff]
    )
    update_export: Export = gql.django.update_mutation(
        ExportInputPartial, permission_classes=[IsStaff]
    )
    delete_export: Export = gql.django.delete_mutation(
        gql.NodeInput, permission_classes=[IsSuperuser]
    )
