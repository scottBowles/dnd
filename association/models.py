from graphql_relay import to_global_id
from nucleus.models import Entity
from django.db import models


class Association(Entity):
    related_associations = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
    )
    related_artifacts = models.ManyToManyField(
        "item.Artifact",
        blank=True,
        related_name="related_associations",
    )
    related_characters = models.ManyToManyField(
        "character.Character",
        blank=True,
        related_name="related_associations",
    )
    related_items = models.ManyToManyField(
        "item.Item",
        blank=True,
        related_name="related_associations",
    )
    related_places = models.ManyToManyField(
        "place.Place",
        blank=True,
        related_name="related_associations",
    )
    related_races = models.ManyToManyField(
        "race.Race",
        blank=True,
        related_name="related_associations",
    )

    def __str__(self):
        return self.name

    def global_id(self):
        return to_global_id("Association", self.id)
