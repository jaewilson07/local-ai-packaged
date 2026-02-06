"""Dependencies for Processing capability agents."""

import logging
from dataclasses import dataclass, field

import httpx
from app.capabilities.processing.openwebui_topics.config import config

from app.core.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class ProcessingDeps(BaseDependencies):
    """Infrastructure dependencies for processing operations (topic classification, etc)."""

    # HTTP client for LLM API calls
    http_client: httpx.AsyncClient | None = None

    # Configuration
    llm_base_url: str = field(default_factory=lambda: config.llm_base_url)
    llm_model: str = field(default_factory=lambda: config.llm_model)
    llm_api_key: str | None = field(default_factory=lambda: config.llm_api_key)
    max_topics: int = field(default_factory=lambda: config.max_topics)

    @property
    def llm_url(self) -> str:
        """Get the LLM API URL for chat completions."""
        return f"{self.llm_base_url.rstrip('/')}/chat/completions"

    async def initialize(self) -> None:
        """
        Initialize all infrastructure connections.

        Raises:
            Exception: If connection initialization fails
        """
        if not self.http_client:
            headers = {"Content-Type": "application/json"}
            if self.llm_api_key:
                headers["Authorization"] = f"Bearer {self.llm_api_key}"

            self.http_client = httpx.AsyncClient(headers=headers, timeout=30.0)
            logger.info(
                "llm_client_initialized",
                extra={
                    "llm_base_url": self.llm_base_url,
                    "llm_model": self.llm_model,
                    "has_api_key": bool(self.llm_api_key),
                },
            )

    async def cleanup(self) -> None:
        """Clean up all infrastructure connections."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("llm_client_closed")

    @classmethod
    def from_settings(
        cls,
        http_client: httpx.AsyncClient | None = None,
        llm_base_url: str | None = None,
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        max_topics: int | None = None,
    ) -> "ProcessingDeps":
        """
        Factory method to create dependencies from settings.

        Args:
            http_client: Optional pre-initialized HTTP client
            llm_base_url: Optional override for LLM base URL
            llm_model: Optional override for LLM model
            llm_api_key: Optional override for LLM API key
            max_topics: Optional override for max topics

        Returns:
            ProcessingDeps instance
        """
        return cls(
            http_client=http_client,
            llm_base_url=llm_base_url or config.llm_base_url,
            llm_model=llm_model or config.llm_model,
            llm_api_key=llm_api_key or config.llm_api_key,
            max_topics=max_topics or config.max_topics,
        )
