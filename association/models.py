from graphql_relay import to_global_id
from nucleus.models import Entity


class Association(Entity):
    def __str__(self):
        return self.name

    def global_id(self):
        return to_global_id("AssociationNode", self.id)
