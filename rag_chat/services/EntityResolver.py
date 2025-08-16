import re
from dataclasses import dataclass

from django.contrib.postgres.search import TrigramSimilarity

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import Alias
from place.models import Place
from race.models import Race


@dataclass
class SearchResult:
    entity_id: int
    entity_type: str
    entity: Association | Character | Item | Artifact | Place | Race
    entity_name: str
    matched_name: str
    similarity: float


ENTITY_MODELS = [Character, Race, Place, Item, Artifact, Association]

# Here a 'gram' is essentially a word
DEFAULTS = {
    "NGRAM_RANGE": (1, 5),  # Generate n-grams from 1 to 5 words
    "MAX_ALIASES_PER_NGRAM": 5,  # Max aliases to return per n-gram
    "MAX_RESULTS": 50,  # Max total entities to return
    "SIMILARITY_THRESHOLD": 0.3,  # Minimum similarity to consider a match
}


class EntityResolver:
    def __init__(
        self,
        threshold: float = DEFAULTS["SIMILARITY_THRESHOLD"],
        max_results: int = DEFAULTS["MAX_RESULTS"],
        ngram_range: tuple = DEFAULTS["NGRAM_RANGE"],
        max_aliases_per_ngram: int = DEFAULTS["MAX_ALIASES_PER_NGRAM"],
    ):
        self.threshold = threshold
        self.max_results = max_results
        self.ngram_range = ngram_range
        self.max_aliases_per_ngram = max_aliases_per_ngram

    def clean_text(self, text: str) -> str:
        """Basic cleanup: remove punctuation, normalize whitespace."""
        return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()

    def generate_ngrams(self, text: str) -> list[str]:
        """Generate 1–5 word n-grams from text."""
        tokens = self.clean_text(text).split()
        ngrams = []
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            ngrams.extend(
                [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
            )
        return ngrams

    def search_aliases(self, query: str):
        """
        Search entity aliases using trigram similarity.
        Returns max_aliases_per_ngram results, each linked to its parent entity.
        """
        alias_qs = (
            Alias.objects.annotate(similarity=TrigramSimilarity("name", query))
            .filter(similarity__gt=self.threshold)
            .order_by("-similarity")[: self.max_aliases_per_ngram]
        )
        return alias_qs

    def resolve(self, query: str):
        """Resolve entities from a free-text query."""
        ngrams = self.generate_ngrams(query)

        found_aliases = (
            Alias.objects.none()
            .union(*[self.search_aliases(ng) for ng in ngrams])
            .order_by("-similarity")
        )

        results = []
        seen_entity_global_ids = set()

        for alias in found_aliases:
            entity = alias.entity
            entity_global_id = entity.global_id()
            if entity_global_id not in seen_entity_global_ids:
                results.append(
                    SearchResult(
                        entity=entity,
                        entity_name=entity.name,
                        matched_name=alias.name,
                        similarity=alias.similarity,
                    )
                )
                seen_entity_global_ids.add(entity_global_id)

            if len(results) >= self.max_results:
                break

        return results
