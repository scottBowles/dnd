from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Sequence, Union

from django.contrib.contenttypes.models import ContentType

from association.models import Association
from character.models import Character
from item.models import Artifact, Item
from nucleus.models import GameLog
from place.models import Place
from race.models import Race


@dataclass
class SourcesV1:
    sources: Sequence[
        Association | Character | Place | Item | Artifact | Race | GameLog
    ]
    version: Literal[1] = 1

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for storage."""
        return {
            "version": self.version,
            "sources": [
                {
                    "type": f"{source._meta.app_label}.{source._meta.model_name}",
                    "id": source.pk,
                }
                for source in self.sources
            ],
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "SourcesV1":
        """Create a SourcesV1 instance from a dict."""
        if data.get("version") != 1:
            raise ValueError("Invalid version for SourcesV1")
        sources = []
        for src in data.get("sources", []):
            content_type = ContentType.objects.get(
                app_label=src["type"].split(".")[0],
                model=src["type"].split(".")[1],
            )
            model_class = content_type.model_class()
            if model_class is not None:
                model_instance = model_class.objects.filter(pk=src["id"]).first()
                if model_instance:
                    sources.append(model_instance)
        return SourcesV1(sources=sources)


# Union of all versions (add new versions here)
SourcesUnion = Union[SourcesV1]

# Current version (update when adding new versions)
CURRENT_SOURCES_VERSION = 1
CurrentSourcesModel = SourcesV1


# Version registry for parsing
SOURCES_VERSION_MAP = {
    1: SourcesV1,
}


def parse_sources(data: dict[str, Any]) -> SourcesUnion:
    """Parse sources data into the correct SourcesUnion type.

    Args:
        data: A JSON string that parses to a dict with 'version' and 'sources' keys
    """

    # Handle versioned format (dict with version and sources)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid sources data format: {type(data)}")

    version = data.get("version", None)
    if version not in SOURCES_VERSION_MAP:
        raise ValueError(f"Unsupported sources version: {version}")

    sources_class = SOURCES_VERSION_MAP[version]

    # For now, we only have V1, but this pattern will work for future versions
    return sources_class.from_json(data)


def create_sources(
    sources: List[Association | Character | Place | Item | Artifact | Race | GameLog],
) -> CurrentSourcesModel:
    """Create a new sources object with the current version."""

    return CurrentSourcesModel(sources=sources, version=CURRENT_SOURCES_VERSION)


def bulk_resolve_sources(
    messages_sources: List[Dict[str, Any]],
) -> List[Association | Character | Place | Item | Artifact | Race | GameLog]:
    """Resolve source model instances from multiple messages' sources data in bulk.

    Instead of calling parse_sources() per message (N×M individual DB queries),
    this groups all source references by content type and fetches each group with
    a single ``filter(pk__in=...)`` query.

    Args:
        messages_sources: list of raw ``message.sources`` dicts, each with
            ``{"version": 1, "sources": [{"type": "app.model", "id": pk}, ...]}``

    Returns:
        Flat list of resolved model instances (order not guaranteed).
    """
    # Group PKs by "app_label.model" key
    pks_by_type: dict[str, list[int]] = defaultdict(list)
    for data in messages_sources:
        if not isinstance(data, dict) or data.get("version") != 1:
            continue
        for src in data.get("sources", []):
            type_key = src.get("type")
            pk = src.get("id")
            if type_key and pk is not None:
                pks_by_type[type_key].append(pk)

    # Bulk-fetch each content type
    results: list[Association | Character | Place | Item | Artifact | Race | GameLog] = []
    for type_key, pks in pks_by_type.items():
        parts = type_key.split(".", 1)
        if len(parts) != 2:
            continue
        ct = ContentType.objects.get(app_label=parts[0], model=parts[1])
        model_class = ct.model_class()
        if model_class is not None:
            results.extend(model_class.objects.filter(pk__in=pks))

    return results
