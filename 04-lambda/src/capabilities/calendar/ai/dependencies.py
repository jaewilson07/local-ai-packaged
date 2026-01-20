"""Dependencies for Calendar capability agents."""

import logging
from dataclasses import dataclass
from typing import Any

from capabilities.calendar.calendar_sync.config import config
from pymongo import AsyncMongoClient

from shared.dependencies import BaseDependencies, MongoDBMixin

logger = logging.getLogger(__name__)


@dataclass
class CalendarDeps(BaseDependencies, MongoDBMixin):
    """Dependencies for calendar capability agents."""

    # Core dependencies
    sync_service: Any | None = None

    # Session context
    session_id: str | None = None

    def __post_init__(self):
        """Initialize mixin attributes."""
        self.mongodb_uri = config.mongodb_uri
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

        # Initialize sync service if not already done
        if not self.sync_service and self.db:
            from capabilities.calendar.calendar_sync.services.sync_service import (
                CalendarSyncService,
            )

            self.sync_service = CalendarSyncService(self.db)
            logger.info("calendar_sync_service_initialized")

    async def cleanup(self) -> None:
        """Clean up external connections."""
        await self.cleanup_mongodb()

    @classmethod
    def from_settings(
        cls, mongo_client: AsyncMongoClient | None = None, session_id: str | None = None
    ) -> "CalendarDeps":
        """Create dependencies from application settings."""
        deps = cls(session_id=session_id)
        if mongo_client:
            deps.mongo_client = mongo_client
            deps.db = mongo_client[config.mongodb_database]
        return deps


__all__ = [
    "CalendarDeps",
]
