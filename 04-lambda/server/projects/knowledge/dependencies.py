"""Dependencies for Knowledge project."""

import logging
from dataclasses import dataclass, field

from server.projects.knowledge.config import config
from server.projects.shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDeps(BaseDependencies):
    """Dependencies for Knowledge project event extraction."""

    # Configuration
    use_llm: bool = field(default_factory=lambda: config.use_llm_by_default)

    async def initialize(self) -> None:
        """Initialize dependencies (no external connections needed for basic extraction)."""
        logger.info("knowledge_deps_initialized", extra={"use_llm": self.use_llm})

    async def cleanup(self) -> None:
        """Clean up dependencies (no cleanup needed)."""
        logger.info("knowledge_deps_cleaned_up")

    @classmethod
    def from_settings(cls, use_llm: bool | None = None, **overrides) -> "KnowledgeDeps":
        """
        Create dependencies from application settings.

        Args:
            use_llm: Whether to use LLM for extraction (defaults to config)
            **overrides: Additional overrides

        Returns:
            KnowledgeDeps instance
        """
        return cls(
            use_llm=use_llm if use_llm is not None else config.use_llm_by_default, **overrides
        )
