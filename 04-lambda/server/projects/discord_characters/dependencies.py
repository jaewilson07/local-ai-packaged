"""Dependencies for Discord Characters Agent."""

from dataclasses import dataclass, field
from typing import Optional
import logging
from pymongo import AsyncMongoClient

from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin
from server.projects.discord_characters.config import config
from server.services.discord_characters import DiscordCharacterManager
from server.services.discord_characters.store import DiscordCharacterStore

logger = logging.getLogger(__name__)


@dataclass
class DiscordCharactersDeps(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the Discord characters agent context."""
    
    # Core dependencies
    character_manager: Optional[DiscordCharacterManager] = None
    
    # Session context
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize mixin attributes."""
        if not hasattr(self, 'mongodb_uri'):
            self.mongodb_uri = config.MONGODB_URL
        if not hasattr(self, 'mongodb_database'):
            self.mongodb_database = config.MONGODB_DB_NAME
    
    async def initialize(self) -> None:
        """
        Initialize external connections.
        
        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        # Initialize MongoDB using mixin
        await self.initialize_mongodb()
        
        # Initialize OpenAI client using mixin
        await self.initialize_openai_client(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OLLAMA_BASE_URL if config.USE_OLLAMA else None
        )
        
        # Initialize character manager
        if not self.character_manager and self.db:
            store = DiscordCharacterStore(config.MONGODB_URL, config.MONGODB_DB_NAME, db=self.db)
            self.character_manager = DiscordCharacterManager(store)
            logger.info("discord_character_manager_initialized")
    
    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.character_manager:
            await self.character_manager.close()
        await self.cleanup_mongodb()
        await self.cleanup_openai_clients()
    
    @classmethod
    def from_settings(
        cls,
        mongo_client: Optional[AsyncMongoClient] = None,
        session_id: Optional[str] = None
    ) -> "DiscordCharactersDeps":
        """Create dependencies from application settings."""
        return cls(
            mongo_client=mongo_client,
            session_id=session_id
        )
