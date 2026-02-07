from typing import Iterable

import strawberry
import strawberry_django
from strawberry import relay

from association import models
from nucleus.permissions import IsStaff, IsSuperuser
from strawberry_django.relay import DjangoListConnection
from nucleus.types import Entity, EntityInput, EntityInputPartial
from place import models


@strawberry_django.type(models.Export)
class Export(Entity, relay.Node):
    pass


@strawberry_django.input(models.Export)
class ExportInput(EntityInput):
    pass


@strawberry_django.partial(models.Export)
class ExportInputPartial(EntityInputPartial, strawberry_django.NodeInput):
    pass


@strawberry.type
class ExportQuery:
    exports: DjangoListConnection[Export] = strawberry_django.connection()

    # @strawberry_django.connection(DjangoListConnection[Export])
    # def exports_connection_filtered(self, name_startswith: str) -> Iterable[Export]:
    #     # Note that this resolver is special. It should not resolve the connection, but
    #     # the iterable of nodes itself. Thus, any arguments defined here will be appended
    #     # to the query, and the pagination of the iterable returned here will be
    #     # automatically handled.
    #     return models.Export.objects.filter(name__startswith=name_startswith)


@strawberry.type
class ExportMutation:
    create_export: Export = strawberry_django.mutations.create(
        ExportInput, permission_classes=[IsStaff]
    )
    update_export: Export = strawberry_django.mutations.update(
        ExportInputPartial, permission_classes=[IsStaff]
    )
    delete_export: Export = strawberry_django.mutations.delete(
        strawberry_django.NodeInput, permission_classes=[IsSuperuser]
    )
