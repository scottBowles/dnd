# rag_chat/content_processors.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from .embeddings import chunk_document, clean_text


class BaseContentProcessor(ABC):
    """
    Abstract base class for processing different content types into embeddings
    """

    content_type: str = None

    @abstractmethod
    def extract_text(self, obj) -> str:
        """Extract searchable text from the object"""
        pass

    @abstractmethod
    def build_metadata(
        self, obj, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        """Build metadata for the content chunk"""
        pass

    @abstractmethod
    def get_object_id(self, obj) -> str:
        """Get a unique identifier for the object"""
        pass

    def should_chunk(self, text: str) -> bool:
        """Determine if text should be split into chunks"""
        # Default: chunk if longer than 1000 words
        return len(text.split()) > 1000

    def process_content(self, obj) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Process an object into text chunks with metadata

        Returns:
            List of (chunk_text, metadata) tuples
        """
        text = self.extract_text(obj)
        if not text or not text.strip():
            return []

        text = clean_text(text)

        if self.should_chunk(text):
            chunks = chunk_document(text)
            results = []
            for i, chunk_text in enumerate(chunks):
                metadata = self.build_metadata(obj, chunk_text, i)
                results.append((chunk_text, metadata))
            return results
        else:
            # Single chunk
            metadata = self.build_metadata(obj, text, 0)
            return [(text, metadata)]


class GameLogProcessor(BaseContentProcessor):
    content_type = "game_log"

    def extract_text(self, game_log) -> str:
        return game_log.log_text or ""

    def get_object_id(self, game_log) -> str:
        return str(game_log.pk)

    def build_metadata(
        self, game_log, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "title": game_log.title or "Untitled Session",
            "session_number": game_log.session_number,
            "session_date": (
                game_log.game_date.isoformat() if game_log.game_date else None
            ),
            "brief_summary": (
                game_log.brief if game_log.brief and len(game_log.brief) < 200 else None
            ),
            "google_doc_url": game_log.url,
            "chunk_index": chunk_index,
        }

        # Add places
        try:
            places = [place.name for place in game_log.places_set_in.all()[:5]]
            if places:
                metadata["places_set_in"] = places
        except:
            pass

        return metadata


class CharacterProcessor(BaseContentProcessor):
    content_type = "character"

    def extract_text(self, character) -> str:
        text_parts = []

        if hasattr(character, "name") and character.name:
            text_parts.append(f"Character Name: {character.name}")

        if hasattr(character, "description") and character.description:
            text_parts.append(f"Description: {character.description}")

        if hasattr(character, "race") and character.race:
            text_parts.append(
                f"Race: {character.race.name if hasattr(character.race, 'name') else str(character.race)}"
            )

        text_parts.append(
            f"Associations: {', '.join(association.name for association in character.associations.all())}"
        )

        return "\n\n".join(text_parts)

    def get_object_id(self, character) -> str:
        return str(character.pk)

    def should_chunk(self, text: str) -> bool:
        # Characters usually don't need chunking unless very detailed
        return len(text.split()) > 1000

    def build_metadata(
        self, character, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(character, "name", "Unknown Character"),
            "chunk_index": chunk_index,
        }

        # Add race info if available
        if hasattr(character, "race") and character.race:
            metadata["race"] = (
                character.race.name
                if hasattr(character.race, "name")
                else str(character.race)
            )

        # Add associated game logs
        try:
            if hasattr(character, "game_logs") and hasattr(character.game_logs, "all"):
                log_titles = [
                    log.title for log in character.game_logs.all() if log.title
                ]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class PlaceProcessor(BaseContentProcessor):
    content_type = "place"

    def extract_text(self, place) -> str:
        text_parts = []

        if hasattr(place, "name") and place.name:
            text_parts.append(f"Place Name: {place.name}")

        if hasattr(place, "description") and place.description:
            text_parts.append(f"Description: {place.description}")

        if hasattr(place, "place_type") and place.place_type:
            text_parts.append(f"Place Type: {place.place_type}")

        if hasattr(place, "parent") and place.parent:
            text_parts.append(f"Is in: {place.parent.name} ({place.parent.place_type})")

        return "\n\n".join(text_parts)

    def get_object_id(self, place) -> str:
        return str(place.pk)

    def should_chunk(self, text: str) -> bool:
        return len(text.split()) > 1200

    def build_metadata(
        self, place, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(place, "name", "Unknown Place"),
            "chunk_index": chunk_index,
        }

        # Add associated game logs
        try:
            if hasattr(place, "logs_set_in") and hasattr(place.logs_set_in, "all"):
                log_titles = [log.title for log in place.logs_set_in.all() if log.title]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class ItemProcessor(BaseContentProcessor):
    content_type = "item"

    def extract_text(self, item) -> str:
        text_parts = []

        if hasattr(item, "name") and item.name:
            text_parts.append(f"Item Name: {item.name}")

        if hasattr(item, "description") and item.description:
            text_parts.append(f"Description: {item.description}")

        return "\n\n".join(text_parts)

    def get_object_id(self, item) -> str:
        return str(item.id)

    def should_chunk(self, text: str) -> bool:
        return len(text.split()) > 800

    def build_metadata(
        self, item, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(item, "name", "Unknown Item"),
            "chunk_index": chunk_index,
        }

        # Add associated game logs
        try:
            if hasattr(item, "logs_set_in") and hasattr(item.logs_set_in, "all"):
                log_titles = [log.title for log in item.logs_set_in.all() if log.title]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class ArtifactProcessor(BaseContentProcessor):
    content_type = "artifact"

    def extract_text(self, artifact) -> str:
        text_parts = []

        if hasattr(artifact, "name") and artifact.name:
            text_parts.append(f"Artifact Name: {artifact.name}")

        if hasattr(artifact, "description") and artifact.description:
            text_parts.append(f"Description: {artifact.description}")

        if hasattr(artifact, "items") and artifact.items.all():
            text_parts.append(
                f"Is a: {', '.join(str(item) for item in artifact.items.all())}"
            )

        return "\n\n".join(text_parts)

    def get_object_id(self, artifact) -> str:
        return str(artifact.id)

    def should_chunk(self, text: str) -> bool:
        return len(text.split()) > 1000

    def build_metadata(
        self, artifact, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(artifact, "name", "Unknown Artifact"),
            "chunk_index": chunk_index,
        }
        # Add associated game logs
        try:
            if hasattr(artifact, "logs_set_in") and hasattr(
                artifact.logs_set_in, "all"
            ):
                log_titles = [
                    log.title for log in artifact.logs_set_in.all() if log.title
                ]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class RaceProcessor(BaseContentProcessor):
    content_type = "race"

    def extract_text(self, race) -> str:
        text_parts = []

        if hasattr(race, "name") and race.name:
            text_parts.append(f"Race Name: {race.name}")

        if hasattr(race, "description") and race.description:
            text_parts.append(f"Description: {race.description}")

        return "\n\n".join(text_parts)

    def get_object_id(self, race) -> str:
        return str(race.id)

    def should_chunk(self, text: str) -> bool:
        return len(text.split()) > 1200

    def build_metadata(
        self, race, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(race, "name", "Unknown Race"),
            "chunk_index": chunk_index,
        }
        # Add associated game logs
        try:
            if hasattr(race, "logs_set_in") and hasattr(race.logs_set_in, "all"):
                log_titles = [log.title for log in race.logs_set_in.all() if log.title]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class AssociationProcessor(BaseContentProcessor):
    content_type = "association"

    def extract_text(self, association) -> str:
        text_parts = []

        if hasattr(association, "name") and association.name:
            text_parts.append(f"Association Name: {association.name}")

        if hasattr(association, "description") and association.description:
            text_parts.append(f"Description: {association.description}")

        return "\n\n".join(text_parts)

    def get_object_id(self, association) -> str:
        return str(association.id)

    def should_chunk(self, text: str) -> bool:
        return len(text.split()) > 1200

    def build_metadata(
        self, association, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "name": getattr(association, "name", "Unknown Association"),
            "chunk_index": chunk_index,
        }
        # Add associated game logs
        try:
            if hasattr(association, "logs_set_in") and hasattr(
                association.logs_set_in, "all"
            ):
                log_titles = [
                    log.title for log in association.logs_set_in.all() if log.title
                ]
                if log_titles:
                    metadata["mentioned_in_sessions"] = log_titles
        except:
            pass

        return metadata


class CustomContentProcessor(BaseContentProcessor):
    """
    Processor for custom/ad-hoc content that doesn't fit other categories
    """

    content_type = "custom"

    def __init__(
        self,
        title: str,
        content: str,
        object_id: str = None,
        metadata: Dict[str, Any] = None,
    ):
        self.title = title
        self.content = content
        self.custom_object_id = object_id or title
        self.custom_metadata = metadata or {}

    def extract_text(self, obj=None) -> str:
        return self.content

    def get_object_id(self, obj=None) -> str:
        return self.custom_object_id

    def build_metadata(
        self, obj=None, chunk_text: str = None, chunk_index: int = 0
    ) -> Dict[str, Any]:
        metadata = {
            "title": self.title,
            "chunk_index": chunk_index,
            **self.custom_metadata,
        }
        return metadata


# Registry of processors
CONTENT_PROCESSORS = {
    "game_log": GameLogProcessor,
    "character": CharacterProcessor,
    "place": PlaceProcessor,
    "item": ItemProcessor,
    "artifact": ArtifactProcessor,
    "race": RaceProcessor,
    "association": AssociationProcessor,
    "custom": CustomContentProcessor,
}


def get_processor(content_type: str) -> BaseContentProcessor:
    """Get the appropriate processor for a content type"""
    processor_class = CONTENT_PROCESSORS.get(content_type)
    if not processor_class:
        raise ValueError(f"No processor found for content type: {content_type}")
    return processor_class()
