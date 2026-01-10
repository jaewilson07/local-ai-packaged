"""Dependencies for Calendar Agent."""

from dataclasses import dataclass, field
from typing import Optional, Any
import logging
from pymongo import AsyncMongoClient

from server.projects.shared.dependencies import BaseDependencies, MongoDBMixin
from server.projects.calendar.config import config

logger = logging.getLogger(__name__)


@dataclass
class CalendarDeps(BaseDependencies, MongoDBMixin):
    """Dependencies injected into the calendar agent context."""
    
    # Core dependencies
    sync_service: Optional[Any] = None
    
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
        
        # Initialize Google Calendar sync service (lazy initialization)
        # We'll create it when needed to avoid import cycles
        if not self.sync_service:
            logger.info("calendar_sync_service_will_be_initialized_on_demand")
    
    def get_sync_service(self) -> Any:
        """Get or create the Google Calendar sync service."""
        if not self.sync_service:
            from server.projects.calendar.services.sync_service import GoogleCalendarSyncService
            from server.projects.calendar.stores.mongodb_store import MongoDBCalendarStore
            
            # Create MongoDB store adapter for sync state
            store = MongoDBCalendarStore(self.db, config.mongodb_collection_sync_state)
            
            self.sync_service = GoogleCalendarSyncService(
                credentials_path=config.google_calendar_credentials_path,
                token_path=config.google_calendar_token_path,
                store=store,
                default_calendar_id=config.google_calendar_id
            )
            logger.info("calendar_sync_service_initialized")
        
        return self.sync_service
    
    async def cleanup(self) -> None:
        """Clean up external connections."""
        await self.cleanup_mongodb()
        
        if self.sync_service:
            self.sync_service = None
    
    @classmethod
    def from_settings(
        cls,
        mongo_client: Optional[AsyncMongoClient] = None,
        session_id: Optional[str] = None
    ) -> "CalendarDeps":
        """Create dependencies from application settings."""
        return cls(
            mongo_client=mongo_client,
            session_id=session_id
        )
