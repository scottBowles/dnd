from algoliasearch_django import AlgoliaIndex
from algoliasearch_django.decorators import register

from .models import Association


@register(Association)
class AssociationIndex(AlgoliaIndex):
    fields = ("global_id", "name", "description", "thumbnail")
    settings = {
        "searchableAttributes": ["name"],
        "customRanking": ["desc(most_recent_log_by_name)", "asc(name)"],
    }
