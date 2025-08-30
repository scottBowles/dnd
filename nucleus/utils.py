from typing import TypeVar
from django.db import models

# Type variable for Django model instances
T = TypeVar("T", bound=models.Model)


def dedupe_model_instances(objects: list[T]) -> list[T]:
    """
    Take a list of Django model instances and return a deduplicated list based on (model, pk)
    """
    seen = set()
    deduped = []
    for obj in objects:
        key = (obj._meta.model_name, obj.pk)
        if key not in seen:
            seen.add(key)
            deduped.append(obj)
    return deduped
