from algoliasearch_django import AlgoliaIndex
from algoliasearch_django.decorators import register

from .models import NPC


@register(NPC)
class NPCIndex(AlgoliaIndex):
    fields = ("global_id", "name", "description", "thumbnail")
    settings = {
        "searchableAttributes": ["name"],
        "customRanking": ["desc(most_recent_log_by_name)", "asc(name)"],
    }
    # on the frontend we changed to using the npc class for all characters.
    # this hasn't been updated on the backend yet (and there's still a chance
    # we'll want to use separate npc and character classes eventually).
    index_name = "Character"
