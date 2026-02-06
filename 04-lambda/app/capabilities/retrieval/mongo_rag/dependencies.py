"""Dependencies for MongoDB RAG Agent."""

import logging
from dataclasses import dataclass, field
from typing import Any

import openai
from app.capabilities.retrieval.graphiti_rag.config import config as graphiti_config
from app.capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps as GraphitiDeps
from app.capabilities.retrieval.mongo_rag.config import config
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies(BaseDependencies):
    """Dependencies injected into the agent context."""

    # Core dependencies
    mongo_client: AsyncMongoClient | None = None
    db: Any | None = None
    openai_client: openai.AsyncOpenAI | None = None
    settings: Any | None = None

    # Graphiti dependencies (optional)
    graphiti_deps: GraphitiDeps | None = None

    # Session context
    session_id: str | None = None
    user_preferences: dict[str, Any] = field(default_factory=dict)
    query_history: list = field(default_factory=list)

    # User context for RLS
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False
    user_groups: list = field(default_factory=list)

    @classmethod
    def from_settings(
        cls,
        mongo_client: AsyncMongoClient | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
        is_admin: bool = False,
        user_groups: list | None = None,
        mongodb_username: str | None = None,
        mongodb_password: str | None = None,
        **kwargs,
    ) -> "AgentDependencies":
        """
        Create dependencies from application settings.

        Args:
            mongo_client: Optional pre-initialized MongoDB client
            session_id: Optional session ID
            user_id: User UUID for RLS
            user_email: User email for RLS
            is_admin: Whether user is admin
            user_groups: List of group IDs user belongs to
            mongodb_username: MongoDB username for user-based auth
            mongodb_password: MongoDB password for user-based auth
            **kwargs: Additional fields
        """
        deps = cls(
            mongo_client=mongo_client,
            session_id=session_id,
            current_user_id=user_id,
            current_user_email=user_email,
            is_admin=is_admin,
            user_groups=user_groups or [],
            **kwargs,
        )
        # Store MongoDB credentials for user-based connection
        if hasattr(deps, "__dict__"):
            deps.__dict__["_mongodb_username"] = mongodb_username
            deps.__dict__["_mongodb_password"] = mongodb_password
        return deps

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

        # Initialize MongoDB client
        if not self.mongo_client:
            try:
                # Use user-based authentication if credentials provided
                mongodb_uri = config.mongodb_uri
                if hasattr(self, "_mongodb_username") and hasattr(self, "_mongodb_password"):
                    mongodb_username = self.__dict__.get("_mongodb_username")
                    mongodb_password = self.__dict__.get("_mongodb_password")

                    if mongodb_username and mongodb_password:
                        # Build user-based connection string
                        # Extract base URI components
                        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

                        parsed = urlparse(config.mongodb_uri)

                        # Build new URI with user credentials
                        # Format: mongodb://username:password@host:port/database?options
                        netloc = f"{mongodb_username}:{mongodb_password}@{parsed.hostname}"
                        if parsed.port:
                            netloc += f":{parsed.port}"

                        # Preserve query parameters
                        query_params = parse_qs(parsed.query)
                        query_params["authSource"] = ["admin"]  # Ensure authSource
                        query_string = urlencode(query_params, doseq=True)

                        mongodb_uri = urlunparse(
                            (
                                parsed.scheme,
                                netloc,
                                parsed.path,
                                parsed.params,
                                query_string,
                                parsed.fragment,
                            )
                        )

                        logger.info(f"Connecting to MongoDB as user: {mongodb_username}")
                    else:
                        logger.info("Using service account for MongoDB connection")
                else:
                    logger.info("Using service account for MongoDB connection")

                self.mongo_client = AsyncMongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
                self.db = self.mongo_client[config.mongodb_database]

                # Verify connection with ping
                await self.mongo_client.admin.command("ping")
                logger.info(
                    "mongodb_connected",
                    extra={
                        "database": config.mongodb_database,
                        "collections": {
                            "documents": config.mongodb_collection_documents,
                            "chunks": config.mongodb_collection_chunks,
                        },
                        "user": self.current_user_email or "service_account",
                    },
                )
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.exception("mongodb_connection_failed", extra={"error": str(e)})
                raise

        # Initialize OpenAI client for embeddings
        if not self.openai_client:
            self.openai_client = openai.AsyncOpenAI(
                api_key=config.embedding_api_key,
                base_url=config.embedding_base_url,
            )
            logger.info(
                "openai_client_initialized",
                extra={
                    "model": config.embedding_model,
                    "dimension": config.embedding_dimension,
                },
            )

        # Initialize Graphiti if enabled
        if graphiti_config.use_graphiti and not self.graphiti_deps:
            try:
                self.graphiti_deps = GraphitiDeps()
                await self.graphiti_deps.initialize()
                if self.graphiti_deps.graphiti:
                    logger.info("graphiti_initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Graphiti: {e}")
                self.graphiti_deps = None

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            logger.info("mongodb_connection_closed")

        if self.graphiti_deps:
            await self.graphiti_deps.cleanup()
            self.graphiti_deps = None

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI-compatible API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        if not self.openai_client:
            await self.initialize()

        try:
            response = await self.openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.exception(f"Embedding generation failed: {e}")
            raise

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference for the session.

        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value

    def add_to_history(self, query: str) -> None:
        """
        Add a query to the search history.

        Args:
            query: Search query to add to history
        """
        self.query_history.append(query)
        # Keep only last 10 queries
        if len(self.query_history) > 10:
            self.query_history.pop(0)
