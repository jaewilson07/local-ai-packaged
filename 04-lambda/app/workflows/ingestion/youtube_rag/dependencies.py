"""Dependencies for YouTube RAG project."""

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from pymongo import AsyncMongoClient
from app.workflows.ingestion.youtube_rag.config import config
from app.workflows.ingestion.youtube_rag.services.youtube_client import YouTubeClient

from app.core.dependencies import BaseDependencies, MongoDBMixin

logger = logging.getLogger(__name__)


@dataclass
class YouTubeRAGDeps(BaseDependencies, MongoDBMixin):
    """
    Dependencies for YouTube RAG operations.

    Inherits from BaseDependencies for standard interface and MongoDBMixin
    for MongoDB connection handling.

    Attributes:
        youtube_client: Client for YouTube API interactions
        openai_client: Client for LLM-based extraction (entities, topics)
        preferred_language: Preferred transcript language code
        skip_mongodb: Skip MongoDB initialization when using ContentIngestionService
    """

    # MongoDB (from MongoDBMixin)
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    mongodb_uri: str = field(default_factory=lambda: config.mongodb_uri)
    mongodb_database: str = field(default_factory=lambda: config.mongodb_database)

    # YouTube-specific
    youtube_client: YouTubeClient | None = None
    openai_client: openai.AsyncOpenAI | None = None

    # Configuration
    preferred_language: str = field(default_factory=lambda: config.default_transcript_language)

    # Skip flags for when using ContentIngestionService
    skip_mongodb: bool = False

    async def initialize(self) -> None:
        """
        Initialize all dependencies.

        - MongoDB client (unless skip_mongodb=True)
        - YouTube client for video data extraction
        - OpenAI client for LLM-based entity/topic extraction (if API key configured)
        """
        # Initialize MongoDB client using mixin (unless skipped)
        if not self.skip_mongodb:
            await self.initialize_mongodb(
                mongodb_uri=self.mongodb_uri,
                mongodb_database=self.mongodb_database,
            )
        else:
            logger.info("MongoDB initialization skipped (using ContentIngestionService)")

        # Initialize YouTube client
        if self.youtube_client is None:
            self.youtube_client = YouTubeClient(
                preferred_language=self.preferred_language,
            )
            logger.info(
                "youtube_client_initialized",
                extra={"preferred_language": self.preferred_language},
            )

        # Initialize OpenAI client for extractors (if API key is configured)
        if self.openai_client is None and config.openai_api_key:
            self.openai_client = openai.AsyncOpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
            )
            logger.info(
                "openai_client_initialized",
                extra={"base_url": config.openai_base_url},
            )

        logger.info("YouTubeRAGDeps initialized")

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Clean up MongoDB using mixin
        if not self.skip_mongodb:
            await self.cleanup_mongodb()

        # YouTube client doesn't need cleanup (no persistent connections)
        self.youtube_client = None

        # OpenAI client doesn't need explicit cleanup
        self.openai_client = None

        logger.info("YouTubeRAGDeps cleaned up")

    @classmethod
    def from_settings(
        cls,
        preferred_language: str | None = None,
        skip_mongodb: bool = False,
        **kwargs,
    ) -> "YouTubeRAGDeps":
        """
        Create dependencies from settings.

        Args:
            preferred_language: Override preferred transcript language
            skip_mongodb: Skip MongoDB initialization (use ContentIngestionService instead)
            **kwargs: Additional fields to pass to constructor

        Returns:
            YouTubeRAGDeps instance (not yet initialized, call initialize() separately)
        """
        return cls(
            preferred_language=preferred_language or config.default_transcript_language,
            skip_mongodb=skip_mongodb,
            **kwargs,
        )
