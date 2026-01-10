"""Transformers-based NER extractor using Hugging Face models.

Modern alternative to spaCy that is fully compatible with Pydantic v2.
Uses pre-trained BERT models for Named Entity Recognition.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
from datetime import datetime

from .models import Entity, EntityType, EntityExtractionResult
from .base import EntityExtractor


class NERExtractor(EntityExtractor):
    """Transformers-based NER using Hugging Face models.

    Uses a thread pool to avoid blocking the event loop since inference is CPU-bound.
    Default model: dslim/bert-base-NER (fine-tuned BERT for NER tasks).
    """

    def __init__(
        self, 
        model_name: str = "Jean-Baptiste/roberta-large-ner-english", 
        max_workers: int = 4,
        aggregation_strategy: str = "simple"
    ) -> None:
        """Initialize the NER extractor.

        Args:
            model_name: Hugging Face model identifier (default: Jean-Baptiste/roberta-large-ner-english)
            max_workers: Number of threads for async execution
            aggregation_strategy: How to aggregate sub-word tokens ("simple", "first", "average", "max")
        """
        self._model_name = model_name
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._aggregation_strategy = aggregation_strategy
        # Lazy-load model in executor to avoid import-time failure
        self._pipeline = None

    def _ensure_model(self):
        """Lazy-load the transformers pipeline."""
        from transformers import pipeline

        if self._pipeline is None:
            self._pipeline = pipeline(
                "ner",
                model=self._model_name,
                aggregation_strategy=self._aggregation_strategy,
            )
        return self._pipeline

    def _map_label(self, label: str) -> EntityType:
        """Map Hugging Face NER labels to our EntityType enum.

        Common labels from dslim/bert-base-NER:
        - PER (Person), ORG (Organization), LOC (Location), MISC (Miscellaneous)
        """
        # Remove B-, I- prefixes from BIO tagging if present
        label_clean = label.replace("B-", "").replace("I-", "")
        
        mapping = {
            "PER": EntityType.PERSON,
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORGANIZATION,
            "ORGANIZATION": EntityType.ORGANIZATION,
            "LOC": EntityType.LOCATION,
            "LOCATION": EntityType.LOCATION,
            "GPE": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.DATE,
            "PRODUCT": EntityType.TECHNOLOGY,
            "MISC": EntityType.CONCEPT,
        }
        return mapping.get(label_clean.upper(), EntityType.CONCEPT)

    def _run_inference(self, text: str) -> List[dict]:
        """Run NER inference in the thread pool."""
        pipeline = self._ensure_model()
        # Truncate long texts to avoid model limits (512 tokens for BERT)
        max_chars = 2000
        if len(text) > max_chars:
            text = text[:max_chars]
        return pipeline(text)

    async def extract(self, text: str) -> EntityExtractionResult:
        """Extract entities from text using transformers NER.

        Args:
            text: Input text to analyze

        Returns:
            EntityExtractionResult with detected entities
        """
        start = datetime.now()

        loop = asyncio.get_event_loop()
        ner_results = await loop.run_in_executor(self._executor, self._run_inference, text)

        entities: List[Entity] = []
        for result in ner_results:
            entities.append(
                Entity(
                    name=result["word"],
                    type=self._map_label(result["entity_group"]),
                    span=(result["start"], result["end"]),
                    confidence=float(result["score"]),
                    source="transformers",
                )
            )

        elapsed_ms = (datetime.now() - start).total_seconds() * 1000.0

        return EntityExtractionResult(
            entities=entities,
            relationships=[],
            chunk_id="",
            extraction_time_ms=elapsed_ms,
            extractor_type="ner",
        )

    def get_supported_types(self) -> List[EntityType]:
        """Return list of entity types this extractor can detect."""
        return [
            EntityType.PERSON,
            EntityType.ORGANIZATION,
            EntityType.LOCATION,
            EntityType.DATE,
            EntityType.TECHNOLOGY,
            EntityType.CONCEPT,
        ]


__all__ = ["NERExtractor"]
