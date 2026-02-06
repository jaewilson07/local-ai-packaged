"""Dependencies for Retrieval capability (vector search + graph search)."""

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from app.capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from app.capabilities.retrieval.mongo_rag.config import config
from pymongo import AsyncMongoClient

from shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class RetrievalDeps(BaseDependencies):
    """Unified dependencies for retrieval operations (vector + graph search)."""

    # MongoDB dependencies (for vector search)
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    openai_client: openai.AsyncOpenAI | None = None

    # Graphiti dependencies (for graph search)
    graphiti_deps: GraphitiRAGDeps | None = None

    # Session and user context
    session_id: str | None = None
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False
    user_groups: list = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    query_history: list = field(default_factory=list)

    @classmethod
    def from_settings(
        cls,
        mongo_client: AsyncMongoClient | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
        is_admin: bool = False,
        user_groups: list | None = None,
        **kwargs,
    ) -> "RetrievalDeps":
        """
        Create dependencies from application settings.

        Args:
            mongo_client: Optional pre-initialized MongoDB client
            session_id: Optional session ID
            user_id: User UUID for RLS
            user_email: User email for RLS
            is_admin: Whether user is admin
            user_groups: List of group IDs user belongs to
            **kwargs: Additional fields

        Returns:
            RetrievalDeps instance
        """
        graphiti_deps = GraphitiRAGDeps.from_settings()

        return cls(
            mongo_client=mongo_client,
            session_id=session_id,
            current_user_id=user_id,
            current_user_email=user_email,
            is_admin=is_admin,
            user_groups=user_groups or [],
            graphiti_deps=graphiti_deps,
            **kwargs,
        )

    async def initialize(self) -> None:
        """Initialize all retrieval infrastructure connections."""
        try:
            # Initialize MongoDB for vector search
            if not self.mongo_client:
                self.mongo_client = AsyncMongoClient(
                    config.mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                )
                self.db = self.mongo_client[config.database_name]
                logger.info("MongoDB client initialized")

            # Initialize OpenAI for embeddings
            if not self.openai_client:
                self.openai_client = openai.AsyncOpenAI(api_key=config.openai_api_key)
                logger.info("OpenAI client initialized")

            # Initialize Graphiti for graph search
            if self.graphiti_deps:
                await self.graphiti_deps.initialize()
                logger.info("Graphiti dependencies initialized")

        except Exception as e:
            logger.exception(f"Failed to initialize retrieval dependencies: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up all retrieval infrastructure connections."""
        try:
            if self.mongo_client:
                self.mongo_client.close()
                self.mongo_client = None
                logger.info("MongoDB client closed")

            if self.openai_client:
                await self.openai_client.close()
                self.openai_client = None
                logger.info("OpenAI client closed")

            if self.graphiti_deps:
                await self.graphiti_deps.cleanup()
                logger.info("Graphiti dependencies cleaned up")

        except Exception as e:
            logger.exception(f"Error during cleanup: {e}")


__all__ = [
    "RetrievalDeps",
]
