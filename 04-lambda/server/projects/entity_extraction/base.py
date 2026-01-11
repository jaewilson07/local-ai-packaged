"""Abstract base classes for entity extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import EntityExtractionResult, EntityType


class EntityExtractor(ABC):
    """Abstract extractor interface for entity detection.

    Implementations must provide async `extract` returning an
    `EntityExtractionResult` and a list of supported entity types.
    """

    @abstractmethod
    async def extract(self, text: str) -> EntityExtractionResult:
        """Extract entities and relationships from text.

        Args:
            text: Text content to analyze

        Returns:
            Structured extraction result
        """

    @abstractmethod
    def get_supported_types(self) -> list[EntityType]:
        """Return the entity types supported by this extractor."""


__all__ = ["EntityExtractor"]
