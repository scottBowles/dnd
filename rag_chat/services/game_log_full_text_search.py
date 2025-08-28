from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from nucleus.models import GameLog


def game_log_fts(query_str, limit=10):
    # Consider changing config to 'english' if this doesn't work well
    # - simple should work better for fantasy names and terms
    # - english will do stemming, stopwords, but may mangle fantasy terms
    query = SearchQuery(query_str, config="simple", search_type="websearch")

    return (
        GameLog.objects.annotate(rank=SearchRank(F("full_text_search_vector"), query))
        .filter(full_text_search_vector__isnull=False)
        .order_by("-rank")[:limit]
    )
