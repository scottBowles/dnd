from dataclasses import dataclass
from typing import Dict, NamedTuple, Sequence

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import GameLog
from place.models import Place
from race.models import Race


EntityOrGameLog = GameLog | Association | Character | Place | Item | Artifact | Race


class ScoreSetElement(NamedTuple):
    data: EntityOrGameLog
    score: float


def z_score_normalize(elements: Sequence[ScoreSetElement]) -> Sequence[ScoreSetElement]:
    mean = sum(s.score for s in elements) / len(elements)
    squared_diffs = [(s.score - mean) ** 2 for s in elements]
    stddev = (sum(squared_diffs) / len(squared_diffs)) ** 0.5 if squared_diffs else 1
    return [
        ScoreSetElement(
            score=(s.score - mean) / stddev if stddev else 1,
            data=s.data,
        )
        for s in elements
    ]


def remove_results_more_than_stddev_below_mean(
    elements: Sequence[ScoreSetElement],
) -> Sequence[ScoreSetElement]:
    if not elements:
        return []

    mean_score = sum(s.score for s in elements) / len(elements)
    stddev = (
        (sum((s.score - mean_score) ** 2 for s in elements) / len(elements)) ** 0.5
        if elements
        else 1
    )
    return [s for s in elements if s.score > mean_score - stddev]


def hybrid_rank_fuse(
    *sets_with_weights: tuple[Sequence[ScoreSetElement], float]
) -> Sequence[ScoreSetElement]:
    """
    hybrid_rank_fuse combines results from multiple search methods, each with a weight.
    """
    all_parts_with_scores: Dict[str, ScoreSetElement] = {}
    for set_data, weight in sets_with_weights:
        for element in set_data:
            existing = all_parts_with_scores.get(element.data.global_id())
            weighted_score = (
                existing.score if existing else 0
            ) + element.score * weight
            all_parts_with_scores[element.data.global_id()] = ScoreSetElement(
                score=weighted_score,
                data=element.data,
            )

    # return a sorted list of ScoreSetElements, excluding scores more than a standard deviation below the mean
    all_parts = list(all_parts_with_scores.values())
    all_parts = sorted(all_parts, key=lambda s: s.score, reverse=True)
    return all_parts
