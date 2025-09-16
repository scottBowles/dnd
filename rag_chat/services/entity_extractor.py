from functools import lru_cache
from typing import List, Set
import re


def clean_text(text: str) -> str:
    """Basic cleanup: remove punctuation, normalize whitespace."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()


class EntityExtractor:
    def extract_ngram_candidates(self, text: str, max_ngram: int = 5) -> Set[str]:
        """Extract n-gram candidates with intelligent filtering"""
        words = text.split()
        candidates = set()

        # Define stop words and common non-entity words
        stop_words = {
            # Question words
            "what",
            "when",
            "where",
            "why",
            "how",
            "who",
            "which",
            "that",
            "this",
            "these",
            "those",
            # Articles and prepositions
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "among",
            "against",
            "under",
            "over",
            "up",
            "down",
            "out",
            "off",
            "near",
            "far",
            # Common verbs that rarely start entity names
            "happened",
            "fight",
            "brokered",
            "went",
            "came",
            "said",
            "told",
            "asked",
            "gave",
            "took",
            "made",
            "did",
            "was",
            "were",
            "is",
            "are",
            "been",
            "being",
            "have",
            "has",
            "had",
            # Other common words
            "all",
            "some",
            "any",
            "each",
            "every",
            "other",
            "another",
            "such",
            "same",
            "different",
            "more",
            "most",
            "less",
            "few",
            "many",
            "much",
            "several",
            "both",
            "either",
            "neither",
        }

        # Extract n-grams of different lengths
        for n in range(1, min(max_ngram + 1, len(words) + 1)):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i : i + n])
                first_word = words[i].lower().strip('.,!?";')

                # Skip if phrase is too short or starts with stop words
                if (
                    len(phrase) >= 3
                    and len(phrase) <= 50
                    and first_word not in stop_words
                    and not any(
                        phrase.lower().strip().startswith(sw + " ") for sw in stop_words
                    )
                ):

                    # Additional quality filters
                    phrase_clean = phrase.strip('.,!?";')

                    # Skip if it's all punctuation or numbers
                    if phrase_clean and not phrase_clean.replace(" ", "").isdigit():
                        candidates.add(phrase_clean)

        return candidates

    @lru_cache(maxsize=500)  # Cache frequent query patterns
    def extract_candidates(self, query_text: str, max_ngram: int = 5) -> List[str]:
        """Extract entity candidates using n-gram approach with smart filtering"""
        # Clean input
        query_text = clean_text(query_text)

        if len(query_text) < 3:
            return []

        # Use n-gram extraction as primary method
        ngram_candidates = self.extract_ngram_candidates(
            query_text, max_ngram=max_ngram
        )

        # If this isn't performant, consider converting to list and sorting by length then
        # taking the first n (longer phrases first as they're more specific)

        return list(ngram_candidates)


# Create global instance
entity_extractor = EntityExtractor()
