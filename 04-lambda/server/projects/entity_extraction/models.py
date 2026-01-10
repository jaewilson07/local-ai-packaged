"""Graph data models and enums for entity extraction and traversal.

Provides type-safe Pydantic models describing entities, relationships,
and extraction results to integrate with Neo4j/Graphiti-style schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple
from datetime import datetime
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Enumeration of supported entity types.

    Includes common NER categories plus domain-friendly types.
    """

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    TECHNOLOGY = "TECHNOLOGY"
    CONCEPT = "CONCEPT"
    DATE = "DATE"
    DOCUMENT = "DOCUMENT"


class RelationType(str, Enum):
    """Relationship types commonly used in KGs."""

    MENTIONS = "MENTIONS"
    WORKS_AT = "WORKS_AT"
    EMPLOYED_BY = "EMPLOYED_BY"
    LOCATED_IN = "LOCATED_IN"
    USES = "USES"
    RELATED_TO = "RELATED_TO"
    AUTHORED_BY = "AUTHORED_BY"


class Entity(BaseModel):
    """Extracted entity with metadata.

    Attributes:
        name: Canonical name for the entity
        type: Entity type classification
        span: Character offsets (start, end) within source text
        confidence: Confidence score in [0, 1]
        properties: Additional attributes (e.g., identifiers)
        source: Origin of extraction ("transformers", "llm", "hybrid")
    """

    name: str
    type: EntityType
    span: Tuple[int, int] = Field(default=(0, 0))
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    properties: Dict[str, str] = Field(default_factory=dict)
    source: str = Field(default="unknown")


class Relationship(BaseModel):
    """Relationship tuple between entities with optional temporal validity.

    Attributes:
        source_entity: Name or ID of source entity
        target_entity: Name or ID of target entity
        relation_type: Relationship type
        confidence: Confidence score in [0, 1]
        properties: Arbitrary attributes (e.g., provenance)
        valid_from: Start of temporal validity
        valid_to: End of temporal validity (optional)
    """

    source_entity: str
    target_entity: str
    relation_type: RelationType
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    properties: Dict[str, str] = Field(default_factory=dict)
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class EntityExtractionResult(BaseModel):
    """Result container for entity extraction on a single chunk.

    Attributes:
        entities: List of extracted entities
        relationships: List of extracted relationships
        chunk_id: Identifier for the source chunk (index or ObjectId)
        extraction_time_ms: Processing time in milliseconds
        extractor_type: Name of extractor ("ner", "llm", "hybrid")
    """

    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    chunk_id: str = ""
    extraction_time_ms: float = 0.0
    extractor_type: str = "unknown"


__all__ = [
    "EntityType",
    "RelationType",
    "Entity",
    "Relationship",
    "EntityExtractionResult",
]
