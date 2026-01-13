"""Dependencies for Discord Characters Agent."""

import logging
from dataclasses import dataclass

from capabilities.persona.discord_characters.config import config
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from server.services.discord_characters import DiscordCharacterManager
from server.services.discord_characters.store import DiscordCharacterStore
from shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin

logger = logging.getLogger(__name__)


@dataclass
class DiscordCharactersDeps(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the Discord characters agent context."""

    # Core dependencies
    character_manager: DiscordCharacterManager | None = None

    # Session context
    session_id: str | None = None

    def __post_init__(self):
        """Initialize mixin attributes."""
        # Convert field() objects to actual values if needed
        # Use config values which now come from global settings
        if (
            (hasattr(self, "mongodb_uri") and not isinstance(self.mongodb_uri, str))
            or not hasattr(self, "mongodb_uri")
            or not self.mongodb_uri
        ):
            self.mongodb_uri = config.MONGODB_URI

        if (
            (hasattr(self, "mongodb_database") and not isinstance(self.mongodb_database, str))
            or not hasattr(self, "mongodb_database")
            or not self.mongodb_database
        ):
            self.mongodb_database = config.MONGODB_DB_NAME

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        try:
            # Initialize MongoDB using mixin
            logger.info(f"Initializing MongoDB connection to: {self._mask_uri(self.mongodb_uri)}")
            await self.initialize_mongodb()
            logger.info(f"Successfully connected to MongoDB database: {self.mongodb_database}")

            # Initialize OpenAI client using mixin
            await self.initialize_openai_client(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OLLAMA_BASE_URL if config.USE_OLLAMA else None,
            )

            # Initialize character manager
            if not self.character_manager and self.db is not None:
                store = DiscordCharacterStore(
                    config.MONGODB_URI, config.MONGODB_DB_NAME, db=self.db
                )
                self.character_manager = DiscordCharacterManager(store)
                logger.info("discord_character_manager_initialized")
        except ConnectionFailure as e:
            logger.error(
                f"MongoDB connection failure. URI: {self._mask_uri(self.mongodb_uri)}, "
                f"Database: {self.mongodb_database}, Error: {e}"
            )
            raise
        except ServerSelectionTimeoutError as e:
            logger.error(
                f"MongoDB server selection timeout (5s). URI: {self._mask_uri(self.mongodb_uri)}, "
                f"Database: {self.mongodb_database}, Error: {e}. "
                f"Check if MongoDB container is running and accessible."
            )
            raise
        except Exception:
            logger.exception(
                f"Unexpected error initializing DiscordCharactersDeps. "
                f"URI: {self._mask_uri(self.mongodb_uri)}, Database: {self.mongodb_database}"
            )
            raise

    def _mask_uri(self, uri: str) -> str:
        """Mask password in MongoDB URI for safe logging."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(uri)
            if parsed.password:
                return uri.replace(f":{parsed.password}@", ":****@")
            return uri
        except Exception:
            return uri

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.character_manager:
            await self.character_manager.close()
        await self.cleanup_mongodb()
        await self.cleanup_openai_clients()

    @classmethod
    def from_settings(
        cls, mongo_client: AsyncMongoClient | None = None, session_id: str | None = None
    ) -> "DiscordCharactersDeps":
        """Create dependencies from application settings."""
        deps = cls(session_id=session_id)
        # Explicitly set MongoDB values to avoid Field() object issues
        deps.mongodb_uri = config.MONGODB_URI
        deps.mongodb_database = config.MONGODB_DB_NAME
        if mongo_client:
            deps.mongo_client = mongo_client
            deps.db = mongo_client[config.MONGODB_DB_NAME]
        return deps
