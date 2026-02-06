"""Shared dependency base classes and mixins for all projects.

Provides base classes and mixins to eliminate duplication across project
dependencies, standardizing initialization, cleanup, and MongoDB/OpenAI client handling.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any

import openai
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings as global_settings
from app.core.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class BaseDependencies(ABC):
    """
    Abstract base class for all project dependencies.

    Provides standard interface for initialization, cleanup, and factory methods.
    All project-specific dependency classes should inherit from this.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize external connections and resources.

        Raises:
            Exception: If initialization fails
        """

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up external connections and resources.
        """

    @classmethod
    @abstractmethod
    def from_settings(cls, **kwargs) -> "BaseDependencies":
        """
        Create dependencies from application settings.

        Args:
            **kwargs: Optional overrides for specific dependencies

        Returns:
            Initialized dependencies instance (not yet initialized, call initialize() separately)
        """


class MongoDBMixin:
    """
    Mixin for MongoDB connection handling.

    Provides common MongoDB client initialization, connection verification,
    and cleanup. Use this mixin in dependency classes that need MongoDB.
    """

    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    mongodb_uri: str = field(default_factory=lambda: global_settings.mongodb_uri)
    mongodb_database: str = field(default_factory=lambda: global_settings.mongodb_database)

    async def initialize_mongodb(
        self,
        mongodb_uri: str | None = None,
        mongodb_database: str | None = None,
        server_selection_timeout_ms: int = 5000,
    ) -> None:
        """
        Initialize MongoDB client and verify connection.

        Args:
            mongodb_uri: MongoDB connection URI (uses instance attribute if not provided)
            mongodb_database: Database name (uses instance attribute if not provided)
            server_selection_timeout_ms: Connection timeout in milliseconds

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        if self.mongo_client:
            return  # Already initialized

        uri = mongodb_uri or self.mongodb_uri
        database = mongodb_database or self.mongodb_database

        try:
            self.mongo_client = AsyncMongoClient(
                uri, serverSelectionTimeoutMS=server_selection_timeout_ms
            )
            self.db = self.mongo_client[database]

            # Verify connection with ping
            await self.mongo_client.admin.command("ping")
            logger.info(
                "mongodb_connected",
                extra={
                    "database": database,
                    "uri": uri.split("@")[-1] if "@" in uri else uri,  # Hide credentials in log
                },
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.exception("mongodb_connection_failed", extra={"error": str(e)})
            raise

    async def cleanup_mongodb(self) -> None:
        """Clean up MongoDB connection."""
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            logger.info("mongodb_connection_closed")


class OpenAIClientMixin:
    """
    Mixin for OpenAI client handling.

    Provides common OpenAI client initialization and cleanup.
    Use this mixin in dependency classes that need OpenAI/embedding clients.
    """

    openai_client: openai.AsyncOpenAI | None = None
    embedding_service: EmbeddingService | None = None

    async def initialize_openai_client(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        """
        Initialize OpenAI client for LLM operations and embedding service.

        Args:
            api_key: OpenAI API key (defaults to global settings)
            base_url: OpenAI base URL (defaults to global settings)
            embedding_model: Embedding model (defaults to global settings)
        """
        if not self.openai_client:
            api_key = api_key or global_settings.llm_api_key
            base_url = base_url or global_settings.llm_base_url

            self.openai_client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            logger.info("openai_client_initialized", extra={"base_url": base_url})

        if not self.embedding_service:
            # EmbeddingService will create its own client from global_settings
            # or use a provided client if needed
            self.embedding_service = EmbeddingService(model=embedding_model)
            logger.info(
                "embedding_service_initialized",
                extra={"model": self.embedding_service.model},
            )

    async def cleanup_openai_clients(self) -> None:
        """Clean up OpenAI clients."""
        # OpenAI clients don't need explicit cleanup, but we can set to None
        self.openai_client = None
        self.embedding_service = None
        logger.info("openai_clients_closed")
