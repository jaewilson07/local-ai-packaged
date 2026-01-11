"""Hybrid extractor combining Transformers NER and LLM enhancement."""

from __future__ import annotations

from datetime import datetime

from fuzzywuzzy import fuzz

from .base import EntityExtractor
from .llm import LLMExtractor
from .models import Entity, EntityExtractionResult
from .ner import NERExtractor


class HybridExtractor(EntityExtractor):
    """Two-stage extraction: NER first, LLM when needed, with deduplication."""

    def __init__(
        self, llm_threshold: float = 0.7, ner_model: str = "Jean-Baptiste/roberta-large-ner-english"
    ) -> None:
        """Initialize hybrid extractor.

        Args:
            llm_threshold: Confidence threshold below which LLM extraction is triggered
            ner_model: Hugging Face model name for NER (default: Jean-Baptiste/roberta-large-ner-english)
        """
        self._ner = NERExtractor(model_name=ner_model)
        self._llm = LLMExtractor()
        self._threshold = llm_threshold

    async def extract(self, text: str) -> EntityExtractionResult:
        start = datetime.now()

        ner_result = await self._ner.extract(text)
        avg_conf = (
            sum(e.confidence for e in ner_result.entities) / len(ner_result.entities)
            if ner_result.entities
            else 0.0
        )

        needs_llm = (
            avg_conf < self._threshold
            or len(ner_result.entities) == 0
            or self._has_complex_context(text)
        )

        if needs_llm:
            llm_result = await self._llm.extract(text)
            merged_entities = self._merge_entities(ner_result.entities, llm_result.entities)
            relationships = llm_result.relationships
            extractor_type = "hybrid"
        else:
            merged_entities = ner_result.entities
            relationships = []
            extractor_type = "ner"

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000.0

        return EntityExtractionResult(
            entities=merged_entities,
            relationships=relationships,
            chunk_id="",
            extraction_time_ms=elapsed_ms,
            extractor_type=extractor_type,
        )

    def get_supported_types(self) -> list[EntityType]:
        # Union of both extractors
        return self._llm.get_supported_types()

    def _has_complex_context(self, text: str) -> bool:
        return len(text) > 500 or ":" in text or text.count(",") > 5

    def _merge_entities(
        self, ner_entities: list[Entity], llm_entities: list[Entity]
    ) -> list[Entity]:
        merged: list[Entity] = []
        used_llm: set[int] = set()

        for n in ner_entities:
            best_idx = -1
            best_score = 0
            for i, l in enumerate(llm_entities):
                if i in used_llm or n.type != l.type:
                    continue
                score = fuzz.ratio(n.name.lower(), l.name.lower())
                if score > best_score:
                    best_score = score
                    best_idx = i
            if best_score > 85 and best_idx != -1:
                l = llm_entities[best_idx]
                merged.append(
                    Entity(
                        name=l.name,
                        type=n.type,
                        span=n.span,
                        confidence=max(n.confidence, l.confidence),
                        properties={**n.properties, **l.properties},
                        source="hybrid",
                    )
                )
                used_llm.add(best_idx)
            else:
                merged.append(n)

        for i, l in enumerate(llm_entities):
            if i not in used_llm:
                merged.append(l)

        return merged


__all__ = ["HybridExtractor"]
