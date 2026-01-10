"""Dependencies for Persona Agent."""

from dataclasses import dataclass, field
from typing import Optional, Any
import logging
from pymongo import AsyncMongoClient
import openai

from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin, OpenAIClientMixin
from server.projects.persona.config import config
from server.projects.persona.stores.mongodb_store import MongoPersonaStore

logger = logging.getLogger(__name__)


@dataclass
class PersonaDeps(BaseDependencies, MongoDBMixin, OpenAIClientMixin):
    """Dependencies injected into the persona agent context."""
    
    # Core dependencies
    persona_store: Optional[MongoPersonaStore] = None
    
    # Session context
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize mixin attributes."""
        if not hasattr(self, 'mongodb_uri'):
            self.mongodb_uri = config.mongodb_uri
        if not hasattr(self, 'mongodb_database'):
            self.mongodb_database = config.mongodb_database
    
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
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
        
        # Initialize persona store
        if not self.persona_store and self.db:
            self.persona_store = MongoPersonaStore(self.db)
            logger.info("persona_store_initialized")
    
    async def cleanup(self) -> None:
        """Clean up external connections."""
        await self.cleanup_mongodb()
        await self.cleanup_openai_clients()
    
    @classmethod
    def from_settings(
        cls,
        mongo_client: Optional[AsyncMongoClient] = None,
        session_id: Optional[str] = None
    ) -> "PersonaDeps":
        """Create dependencies from application settings."""
        return cls(
            mongo_client=mongo_client,
            session_id=session_id
        )
