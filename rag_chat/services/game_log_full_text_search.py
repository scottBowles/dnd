import re

import nltk
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, QuerySet

from nucleus.models import GameLog, Entity


def game_log_simple_fts(query_str, limit=10):
    # Consider changing config to 'english' if this doesn't work well
    # - simple should work better for fantasy names and terms
    # - english will do stemming, stopwords, but may mangle fantasy terms
    query = SearchQuery(query_str, config="simple", search_type="websearch")

    return (
        GameLog.objects.annotate(rank=SearchRank(F("full_text_search_vector"), query))
        .filter(full_text_search_vector__isnull=False)
        .order_by("-rank")[:limit]
    )


STOPWORDS = set(nltk.corpus.stopwords.words("english"))


def key_terms(description: str, max_terms: int = 5) -> list[str]:
    """
    Extract salient nouns/adjectives from a description.
    """
    if not description:
        return []

    tokens = nltk.word_tokenize(description)
    tagged = nltk.pos_tag(tokens)

    candidates = [
        word.lower()
        for word, tag in tagged
        if (tag.startswith("NN") or tag.startswith("JJ"))
    ]

    filtered = [w for w in candidates if w not in STOPWORDS and w.isalpha()]

    # Deduplicate while preserving order
    seen = set()
    unique = [w for w in filtered if not (w in seen or seen.add(w))]

    return unique[:max_terms]


def fts_terms(entities: list[Entity]) -> tuple[list[str], list[str]]:
    """
    Build the FTS term list for a user query and matched entities.

    Args:
        entities: list of matched entity objects (with .name, .aliases, .type, .description)

    Returns:
        list[str] for OR-based full-text search
    """
    names_and_aliases = []
    description_keywords = []

    for entity in entities:
        # Canonical name
        if entity.name:
            names_and_aliases.append(entity.name)

        # Aliases
        for alias in entity.aliases.all():
            if alias.name and alias.name not in names_and_aliases:
                names_and_aliases.append(alias.name)

        # Key terms from description
        for term in key_terms(entity.description, max_terms=5):
            if term not in description_keywords:
                description_keywords.append(term)

    return names_and_aliases, description_keywords


def sanitize_term(term: str) -> str:
    """Remove unsafe characters for Postgres FTS raw query."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", term)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def make_entity_query(terms: list[str], config: str = "simple") -> SearchQuery:
    """
    Build a SearchQuery optimized for entity names using plain search.
    This is more reliable and better for exact name matching than raw queries.
    """
    if len(terms) == 0:
        return SearchQuery("", config=config, search_type="plain")

    # Join terms with spaces - plainto_tsquery will handle OR logic automatically
    # and is much more reliable than raw queries for entity names
    query_str = " ".join(terms)
    return SearchQuery(query_str, config=config, search_type="plain")


def weighted_fts_search_logs(
    query: str, entities: list[Entity], limit: int | None = None
) -> QuerySet[GameLog]:
    """
    Perform a weighted full-text search on GameLog entries using the user query and matched entities.

    Args:
        query: the original user query string
        entities: list of matched entity objects (with .name, .aliases, .type, .description)

    Returns:
        QuerySet of GameLog entries
    """
    names_and_aliases, description_keywords = fts_terms(entities)

    # Build the query for each weight category
    user_query_1 = SearchQuery(query.strip(), config="simple", search_type="websearch")
    entity_name_alias_query_2 = make_entity_query(names_and_aliases)
    entity_description_query_3 = make_entity_query(description_keywords)

    # Perform the search using the queries
    results = (
        GameLog.objects.annotate(
            rank_raw=SearchRank(F("full_text_search_vector"), user_query_1),
            rank_names=SearchRank(
                F("full_text_search_vector"), entity_name_alias_query_2
            ),
            rank_keywords=SearchRank(
                F("full_text_search_vector"), entity_description_query_3
            ),
        )
        .annotate(
            rank=F("rank_raw") * 3.0 + F("rank_names") * 2.0 + F("rank_keywords") * 1.0
        )
        .filter(rank__gt=0.1)
        .order_by("-rank")
    )

    return results[:limit] if limit is not None else results
