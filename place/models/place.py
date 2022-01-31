from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError

from nucleus.models import Entity
from .details import PlaceDetails


def validate_none(value):
    if value is not None:
        raise ValidationError("Planet cannot have a parent")


class Planet(Entity):
    details = models.OneToOneField(PlaceDetails, on_delete=models.CASCADE)
    parent = models.PositiveSmallIntegerField(
        blank=True, null=True, default=None, editable=False, validators=[validate_none]
    )


class Region(Entity):
    details = models.OneToOneField(PlaceDetails, on_delete=models.CASCADE)
    parent = models.ForeignKey(Planet, on_delete=models.SET_NULL, null=True, blank=True)


class Town(Entity):
    details = models.OneToOneField(PlaceDetails, on_delete=models.CASCADE)

    parent_choices = ["planet", "region"]
    parent_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(app_label="place", model__in=parent_choices),
        related_name="%(app_label)s_%(class)s_parent",
    )
    parent_object_id = models.PositiveIntegerField()
    parent = GenericForeignKey("parent_content_type", "parent_object_id")


class District(Entity):
    details = models.OneToOneField(PlaceDetails, on_delete=models.CASCADE)

    parent_choices = ["planet", "region", "town"]
    parent_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(app_label="place", model__in=parent_choices),
        related_name="%(app_label)s_%(class)s_parent",
    )
    parent_object_id = models.PositiveIntegerField()
    parent = GenericForeignKey("parent_content_type", "parent_object_id")


class Location(Entity):
    details = models.OneToOneField(PlaceDetails, on_delete=models.CASCADE)

    parent_choices = ["planet", "region", "town", "district"]
    parent_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=models.Q(app_label="place", model__in=parent_choices),
        related_name="%(app_label)s_%(class)s_parent",
    )
    parent_object_id = models.PositiveIntegerField()
    parent = GenericForeignKey("parent_content_type", "parent_object_id")
