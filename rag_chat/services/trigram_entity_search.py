import re
from dataclasses import dataclass

from django.contrib.postgres.search import TrigramSimilarity

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import Alias
from place.models import Place
from race.models import Race
from collections import namedtuple

ENTITY_MODELS = [Character, Race, Place, Item, Artifact, Association]

NGramRange = namedtuple("NGramRange", ["min", "max"])


# Here a 'gram' is essentially a word
@dataclass
class EntityResolverConfig:
    # Minimum similarity value to consider the entity a match
    threshold: float = 0.3
    # Max total entities to return
    max_results: int = 50
    # Generate n-grams from min to max words, to search phrases of word lengths in this range
    ngram_range: NGramRange = NGramRange(
        min=1,
        max=5,
    )
    # Max aliases to return per n-gram, in case a given word or phrase matches multiple aliases
    max_aliases_per_ngram: int = 5


@dataclass
class SearchResult:
    entity_id: int
    entity_type: str
    entity: Association | Character | Item | Artifact | Place | Race
    entity_name: str
    matched_name: str
    similarity: float


def clean_text(text: str) -> str:
    """Basic cleanup: remove punctuation, normalize whitespace."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()


def generate_ngrams(text: str, ngram_range: NGramRange) -> list[str]:
    """Generate 1–5 word n-grams from text."""
    tokens = clean_text(text).split()
    ngrams = []
    for n in range(ngram_range.min, ngram_range.max + 1):
        ngrams.extend([" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)])
    return ngrams


def search_aliases(query: str, threshold: float, max_aliases_per_ngram: int):
    """
    Search entity aliases using trigram similarity.
    Returns max_aliases_per_ngram results, each linked to its parent entity.
    """
    alias_qs = (
        Alias.objects.annotate(similarity=TrigramSimilarity("name", query))
        .filter(similarity__gt=threshold)
        .order_by("-similarity")[:max_aliases_per_ngram]
    )
    return alias_qs


def find_entities_by_trigram_similarity(
    query: str, config: EntityResolverConfig = EntityResolverConfig()
) -> list[SearchResult]:
    """Resolve entities from a free-text query."""
    ngrams = generate_ngrams(query, config.ngram_range)

    found_aliases = (
        Alias.objects.none()
        .union(
            *[
                search_aliases(ng, config.threshold, config.max_aliases_per_ngram)
                for ng in ngrams
            ]
        )
        .order_by("-similarity")
    )

    results: list[SearchResult] = []
    seen_entity_global_ids = set()

    for alias in found_aliases:
        entity = alias.entity
        entity_global_id = entity.global_id()
        if entity_global_id not in seen_entity_global_ids:
            results.append(
                SearchResult(
                    entity_id=entity.id,
                    entity_type=entity.__class__.__name__,
                    entity=entity,
                    entity_name=entity.name,
                    matched_name=alias.name,
                    similarity=alias.similarity,
                )
            )
            seen_entity_global_ids.add(entity_global_id)

        if len(results) >= config.max_results:
            break

    return results
