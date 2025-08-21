from pydantic import BaseModel
from typing import List, Optional, Union, Literal


class GameLogSource(BaseModel):
    type: Literal["game_log"] = "game_log"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    session_number: Optional[int] = None
    title: str
    url: str
    session_date: Optional[str] = None
    places: List[str] = []


class CharacterSource(BaseModel):
    type: Literal["character"] = "character"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []
    race: Optional[str] = None


class PlaceSource(BaseModel):
    type: Literal["place"] = "place"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []


class ItemSource(BaseModel):
    type: Literal["item"] = "item"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []
    item_type: Optional[str] = None


class ArtifactSource(BaseModel):
    type: Literal["artifact"] = "artifact"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []


class RaceSource(BaseModel):
    type: Literal["race"] = "race"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []


class AssociationSource(BaseModel):
    type: Literal["association"] = "association"
    chunk_id: Optional[int] = None
    similarity: float
    chunk_index: int
    name: str
    mentioned_in_sessions: List[str] = []


# Union type for all sources
SourceUnion = Union[
    GameLogSource,
    CharacterSource,
    PlaceSource,
    ItemSource,
    ArtifactSource,
    RaceSource,
    AssociationSource,
]


def parse_source(source: dict) -> SourceUnion:
    """Parse a dict into the correct SourceUnion type."""
    type_map = {
        "game_log": GameLogSource,
        "character": CharacterSource,
        "place": PlaceSource,
        "item": ItemSource,
        "artifact": ArtifactSource,
        "race": RaceSource,
        "association": AssociationSource,
    }
    t = source.get("type")
    model = type_map.get(t)
    if model:
        return model.parse_obj(source)
    raise ValueError(f"Unknown source type: {t}")
