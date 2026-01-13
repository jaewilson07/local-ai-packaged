"""Dependencies for YouTube RAG project."""

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from pymongo import AsyncMongoClient

from server.projects.youtube_rag.config import config
from server.projects.youtube_rag.services.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)


@dataclass
class YouTubeRAGDeps:
    """Dependencies for YouTube RAG operations."""

    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    youtube_client: YouTubeClient | None = None
    openai_client: openai.AsyncOpenAI | None = None

    # Configuration
    preferred_language: str = field(default_factory=lambda: config.default_transcript_language)

    # Skip flags for when using ContentIngestionService
    skip_mongodb: bool = False

    async def initialize(self) -> None:
        """Initialize all dependencies."""
        # Initialize MongoDB client (unless skipped)
        if not self.skip_mongodb and self.mongo_client is None:
            logger.info(f"Connecting to MongoDB at {config.mongodb_uri}")
            self.mongo_client = AsyncMongoClient(config.mongodb_uri)
            self.db = self.mongo_client[config.mongodb_database]
        elif self.skip_mongodb:
            logger.info("MongoDB initialization skipped (using ContentIngestionService)")

        # Initialize YouTube client
        if self.youtube_client is None:
            self.youtube_client = YouTubeClient(
                preferred_language=self.preferred_language,
            )

        # Initialize OpenAI client for extractors
        if self.openai_client is None and config.openai_api_key:
            self.openai_client = openai.AsyncOpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
            )

        logger.info("YouTubeRAGDeps initialized")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.mongo_client:
            self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            logger.info("MongoDB client closed")

    @classmethod
    def from_settings(
        cls,
        preferred_language: str | None = None,
        skip_mongodb: bool = False,
    ) -> "YouTubeRAGDeps":
        """
        Create dependencies from settings.

        Args:
            preferred_language: Override preferred transcript language
            skip_mongodb: Skip MongoDB initialization (use ContentIngestionService instead)

        Returns:
            YouTubeRAGDeps instance
        """
        return cls(
            preferred_language=preferred_language or config.default_transcript_language,
            skip_mongodb=skip_mongodb,
        )
