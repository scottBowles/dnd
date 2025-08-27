from pydantic import BaseModel
from typing import Union, Literal


class SourceV1(BaseModel):
    source_version: Literal[1] = 1
    type: (
        Literal["gamelog"]
        | Literal["character"]
        | Literal["place"]
        | Literal["item"]
        | Literal["artifact"]
        | Literal["race"]
        | Literal["association"]
    )
    id: int


# Union type for all sources
SourceUnion = Union[SourceV1,]


def parse_source(source: dict) -> SourceUnion:
    """Parse a dict into the correct SourceUnion type."""
    source_map = {
        1: SourceV1,
    }
    version = source.get("source_version", 1)
    model = source_map.get(version)
    if model:
        return model.model_validate(source)
    raise ValueError(f"Unknown source version: {version}")
