from algoliasearch_django import AlgoliaIndex
from algoliasearch_django.decorators import register

from .models import Artifact, Item


@register(Item)
class ItemIndex(AlgoliaIndex):
    fields = ("global_id", "name", "description", "thumbnail")
    settings = {
        "searchableAttributes": ["name"],
        "customRanking": ["desc(most_recent_log_by_name)", "asc(name)"],
    }


@register(Artifact)
class ArtifactIndex(AlgoliaIndex):
    fields = ("global_id", "name", "description", "thumbnail")
    settings = {
        "searchableAttributes": ["name"],
        "customRanking": ["desc(most_recent_log_by_name)", "asc(name)"],
    }
