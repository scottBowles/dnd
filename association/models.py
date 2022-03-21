from nucleus.models import Entity


class Association(Entity):
    def __str__(self):
        return self.name
