"""Dependencies for Calendar Agent."""

import logging
from dataclasses import dataclass
from typing import Any

from pymongo import AsyncMongoClient
from src.capabilities.calendar.calendar_sync.config import config
from src.shared.dependencies import BaseDependencies, MongoDBMixin

logger = logging.getLogger(__name__)


@dataclass
class CalendarDeps(BaseDependencies, MongoDBMixin):
    """Dependencies injected into the calendar agent context."""

    # Core dependencies
    sync_service: Any | None = None

    # Session context
    session_id: str | None = None

    def __post_init__(self):
        """Initialize mixin attributes."""
        # Always set MongoDB fields from config to ensure they're strings, not Field objects
        # The mixin's field() definitions don't work properly when mixed into dataclasses
        self.mongodb_uri = config.mongodb_uri
        self.mongodb_database = config.mongodb_database

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        # Initialize MongoDB with user-based auth if credentials provided
        if not self.mongo_client:
            try:
                # Use user-based authentication if credentials provided
                mongodb_uri = self.mongodb_uri
                if hasattr(self, "_mongodb_username") and hasattr(self, "_mongodb_password"):
                    mongodb_username = self.__dict__.get("_mongodb_username")
                    mongodb_password = self.__dict__.get("_mongodb_password")

                    if mongodb_username and mongodb_password:
                        # Build user-based connection string
                        # Extract base URI components
                        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

                        parsed = urlparse(self.mongodb_uri)

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

                # Create MongoDB client with the appropriate URI
                self.mongo_client = AsyncMongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
                self.db = self.mongo_client[self.mongodb_database]

                # Verify connection with ping
                await self.mongo_client.admin.command("ping")
                logger.info(
                    "mongodb_connected",
                    extra={
                        "database": self.mongodb_database,
                        "uri": mongodb_uri.split("@")[-1] if "@" in mongodb_uri else mongodb_uri,
                    },
                )
            except Exception:
                logger.exception("Failed to initialize MongoDB")
                raise
        else:
            # Use existing client - verify connection
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
                default_calendar_id=config.google_calendar_id,
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
        mongo_client: AsyncMongoClient | None = None,
        session_id: str | None = None,
        mongodb_username: str | None = None,
        mongodb_password: str | None = None,
    ) -> "CalendarDeps":
        """
        Create dependencies from application settings.

        Args:
            mongo_client: Optional pre-initialized MongoDB client
            session_id: Optional session ID
            mongodb_username: MongoDB username for user-based auth
            mongodb_password: MongoDB password for user-based auth
        """
        deps = cls(session_id=session_id)
        if mongo_client:
            deps.mongo_client = mongo_client
            deps.db = mongo_client[config.mongodb_database]
        # Store MongoDB credentials for user-based connection
        if hasattr(deps, "__dict__"):
            deps.__dict__["_mongodb_username"] = mongodb_username
            deps.__dict__["_mongodb_password"] = mongodb_password
        return deps
