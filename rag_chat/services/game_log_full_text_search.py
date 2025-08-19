from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from nucleus.models import GameLog


def game_log_fts(query_str, limit=10):
    query = SearchQuery(query_str, config="simple")
    return (
        GameLog.objects.annotate(rank=SearchRank(F("full_text_search_vector"), query))
        .filter(full_text_search_vector=query)
        .order_by("-rank")[:limit]
    )
