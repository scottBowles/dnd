from collections import namedtuple
from dataclasses import dataclass

from django.contrib.postgres.search import TrigramSimilarity

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import Alias
from place.models import Place
from race.models import Race

from .entity_extractor import entity_extractor


@dataclass
class SearchResult:
    entity_id: int
    entity_type: str
    entity: Association | Character | Item | Artifact | Place | Race
    entity_name: str
    matched_name: str
    similarity: float


def trigram_entity_search(
    query_text: str,
    similarity_threshold: float = 0.3,
    max_results: int = 20,
    max_ngram: int = 5,
    max_aliases_per_ngram: int = 2,
    min_alias_length: int = 4,
) -> list[SearchResult]:
    """
    Find entities mentioned in a query using NER + trigram similarity.

    Args:
        query_text: The user's query (can be long)
        limit: Maximum number of entities to return
        similarity_threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of dicts with keys: id, name, entity_id, similarity, matched_phrase
    """
    if not query_text.strip():
        return []

    # Extract potential entity mentions
    candidates = entity_extractor.extract_candidates(query_text, max_ngram=max_ngram)

    if not candidates:
        return []

    # Search for each candidate phrase
    all_matches = []

    for candidate in candidates:
        # Query database with trigram similarity
        matches = (
            Alias.objects.annotate(similarity=TrigramSimilarity("name", candidate))
            .filter(similarity__gt=similarity_threshold)
            .extra(where=["CHAR_LENGTH(name) >= %s"], params=[min_alias_length])
            .order_by("-similarity")[:max_aliases_per_ngram]
        )

        all_matches.extend(list(matches))

    AliasEntity = namedtuple("AliasEntity", ["alias", "entity"])

    # Deduplicate by entity_id, keeping highest similarity
    entity_matches: dict[int, AliasEntity] = {}
    for m in all_matches:
        entity = m.entity
        entity_id = entity.pk
        if (
            entity_id not in entity_matches
            or m.similarity > entity_matches[entity_id].alias.similarity
        ):
            entity_matches[entity_id] = AliasEntity(alias=m, entity=entity)

    # Sort by similarity and limit results
    aliases_with_entities = sorted(
        entity_matches.values(), key=lambda x: x.alias.similarity, reverse=True
    )[:max_results]

    results: list[SearchResult] = []

    for r in aliases_with_entities:
        alias = r.alias
        entity = r.entity
        results.append(
            SearchResult(
                entity_id=entity.pk,
                entity_type=entity.__class__.__name__,
                entity=entity,
                entity_name=entity.name,
                matched_name=alias.name,
                similarity=alias.similarity,
            )
        )

    return results


def search_entities_simple(
    query_text: str, limit: int = 20, similarity_threshold: float = 0.3
) -> list[SearchResult]:
    """
    Fallback: Direct trigram search on entire query (for short queries).
    """
    aliases = (
        Alias.objects.annotate(similarity=TrigramSimilarity("name", query_text))
        .filter(similarity__gt=similarity_threshold)
        .order_by("-similarity")[:limit]
    )

    results: list[SearchResult] = []

    for alias in aliases:
        entity = alias.entity
        results.append(
            SearchResult(
                entity_id=entity.pk,
                entity_type=entity.__class__.__name__,
                entity=entity,
                entity_name=entity.name,
                matched_name=alias.name,
                similarity=alias.similarity,
            )
        )

    return results
