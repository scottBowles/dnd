from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from nucleus.models import Entity


class Artifact(Entity):
    # related_items = GenericRelation(ArtifactItem, related_query_name="artifact")
    pass


class ArtifactItem(models.Model):
    artifact = models.ForeignKey(
        Artifact, on_delete=models.CASCADE, related_name="related_items"
    )
    limit = models.Q(app_label="item")
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, limit_choices_to=limit
    )
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
