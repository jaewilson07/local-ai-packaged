"""Dependencies for Crawl4AI RAG Agent."""

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from crawl4ai import AsyncWebCrawler, BrowserConfig
from pymongo import AsyncMongoClient

from server.projects.crawl4ai_rag.config import config
from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin

logger = logging.getLogger(__name__)


@dataclass
class Crawl4AIDependencies(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the crawl4ai agent context."""

    # Core dependencies
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    openai_client: openai.AsyncOpenAI | None = None
    crawler: AsyncWebCrawler | None = None
    settings: Any | None = None

    # Session context
    session_id: str | None = None
    user_preferences: dict[str, Any] = field(default_factory=dict)

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
            ValueError: If settings cannot be loaded
        """
        if not self.settings:
            self.settings = config
            logger.info("settings_loaded", extra={"database": config.mongodb_database})

        # Initialize MongoDB using mixin
        await self.initialize_mongodb(
            mongodb_uri=config.mongodb_uri, mongodb_database=config.mongodb_database
        )
        logger.info(
            "mongodb_connected",
            extra={
                "database": config.mongodb_database,
                "collections": {
                    "documents": config.mongodb_collection_documents,
                    "chunks": config.mongodb_collection_chunks,
                },
            },
        )

        # Initialize OpenAI client using mixin
        await self.initialize_openai_client(
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            embedding_api_key=config.embedding_api_key,
            embedding_base_url=config.embedding_base_url,
        )
        logger.info(
            "openai_client_initialized",
            extra={
                "model": config.embedding_model,
                "dimension": config.embedding_dimension,
            },
        )

        # Initialize Crawl4AI crawler
        if not self.crawler:
            try:
                browser_config = BrowserConfig(
                    headless=config.browser_headless,
                    verbose=False,
                    text_mode=True,  # Disable images for faster crawling
                )
                self.crawler = AsyncWebCrawler(config=browser_config)
                await self.crawler.__aenter__()
                logger.info("crawl4ai_crawler_initialized")
            except Exception as e:
                logger.exception("crawl4ai_initialization_failed", extra={"error": str(e)})
                raise

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.crawler:
            try:
                await self.crawler.__aexit__(None, None, None)
                self.crawler = None
                logger.info("crawl4ai_crawler_closed")
            except Exception as e:
                logger.warning(f"Error closing crawler: {e}")

        # Cleanup using mixins
        await self.cleanup_mongodb()
        await self.cleanup_openai_clients()

    @classmethod
    def from_settings(cls, **kwargs) -> "Crawl4AIDependencies":
        """
        Create dependencies from application settings.

        Args:
            **kwargs: Optional overrides for specific dependencies

        Returns:
            Initialized dependencies instance (not yet initialized, call initialize() separately)
        """
        return cls(**kwargs)

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        if not self.openai_client:
            await self.initialize()

        response = await self.openai_client.embeddings.create(
            model=config.embedding_model, input=text
        )
        # Return as list of floats - MongoDB stores as native array
        return response.data[0].embedding

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference for the session.

        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value
