"""LLM-based entity extractor using Pydantic AI structured outputs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from server.config import settings

from .base import EntityExtractor
from .models import Entity, EntityExtractionResult, EntityType, Relationship, RelationType


class LLMEntity(BaseModel):
    """Structured entity returned from LLM."""

    name: str
    type: EntityType
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    properties: dict[str, str] = Field(default_factory=dict)


class LLMRelationship(BaseModel):
    """Structured relationship returned from LLM."""

    source: str
    target: str
    type: RelationType
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    properties: dict[str, str] = Field(default_factory=dict)


class LLMExtraction(BaseModel):
    """Overall structured extraction from LLM."""

    entities: list[LLMEntity] = Field(default_factory=list)
    relationships: list[LLMRelationship] = Field(default_factory=list)


class LLMExtractor(EntityExtractor):
    """Entity extractor powered by an LLM with structured outputs."""

    def __init__(self) -> None:
        # Create LLM model from settings
        provider = OpenAIProvider(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        model = OpenAIModel(settings.llm_model, provider=provider)

        self._agent = Agent(
            model,
            result_type=LLMExtraction,
            system_prompt=(
                "You are an expert entity extraction system. "
                "Extract named entities and relationships from the text. "
                "Focus on domain-specific entities that standard NER might miss. "
                "Return high-confidence results only."
            ),
        )

    async def extract(self, text: str) -> EntityExtractionResult:
        start = datetime.now()
        result = await self._agent.run(text)
        data: LLMExtraction = result.data

        entities = [
            Entity(
                name=e.name,
                type=e.type,
                span=(0, 0),
                confidence=e.confidence,
                properties=e.properties,
                source="llm",
            )
            for e in data.entities
        ]

        relationships = [
            Relationship(
                source_entity=r.source,
                target_entity=r.target,
                relation_type=r.type,
                confidence=r.confidence,
                properties=r.properties,
            )
            for r in data.relationships
        ]

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000.0

        return EntityExtractionResult(
            entities=entities,
            relationships=relationships,
            chunk_id="",
            extraction_time_ms=elapsed_ms,
            extractor_type="llm",
        )

    def get_supported_types(self) -> list[EntityType]:
        # LLM can detect all supported types
        return list(EntityType)


__all__ = ["LLMExtractor"]
