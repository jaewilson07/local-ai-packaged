"""MongoDB store for calendar sync state.

This module provides MongoDB persistence for calendar synchronization state,
tracking the mapping between external event IDs and Google Calendar event IDs.
"""

import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SyncState(BaseModel):
    """Model for calendar sync state stored in MongoDB."""

    external_id: str = Field(..., description="External system's event identifier")
    google_event_id: str = Field(..., description="Google Calendar event ID")
    user_id: str = Field(..., description="User who owns this sync state")
    persona_id: str | None = Field(None, description="Persona ID if applicable")
    calendar_id: str = Field("primary", description="Google Calendar ID")
    source_system: str = Field("manual", description="Source system name")
    synced_at: datetime = Field(default_factory=datetime.utcnow, description="Last sync timestamp")
    event_hash: str | None = Field(None, description="Hash of event data for change detection")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MongoDBCalendarStore:
    """MongoDB-based storage for calendar sync state.

    Provides CRUD operations for sync state documents, enabling
    duplicate detection and change tracking for calendar synchronization.
    """

    COLLECTION_NAME = "calendar_sync_state"

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize the store with a MongoDB database.

        Args:
            db: Motor async MongoDB database instance
        """
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
        self._indexes_created = False

    async def ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if self._indexes_created:
            return

        # Compound unique index on user + persona + external_id
        await self.collection.create_index(
            [("user_id", 1), ("persona_id", 1), ("external_id", 1)],
            unique=True,
            name="user_persona_external_unique",
        )

        # Index for looking up by Google event ID
        await self.collection.create_index(
            [("google_event_id", 1)],
            name="google_event_id_idx",
        )

        # Index for listing by user
        await self.collection.create_index(
            [("user_id", 1), ("synced_at", -1)],
            name="user_synced_at_idx",
        )

        self._indexes_created = True
        logger.info("calendar_sync_indexes_created")

    async def get_by_external_id(
        self,
        user_id: str,
        persona_id: str | None,
        external_id: str,
    ) -> SyncState | None:
        """
        Get sync state by external ID.

        Args:
            user_id: User who owns the sync state
            persona_id: Persona ID (can be None)
            external_id: External system's event identifier

        Returns:
            SyncState if found, None otherwise
        """
        await self.ensure_indexes()

        query = {
            "user_id": user_id,
            "external_id": external_id,
        }
        if persona_id:
            query["persona_id"] = persona_id
        else:
            query["persona_id"] = None

        doc = await self.collection.find_one(query)
        if doc:
            doc.pop("_id", None)
            return SyncState(**doc)
        return None

    async def get_by_google_event_id(
        self,
        google_event_id: str,
    ) -> SyncState | None:
        """
        Get sync state by Google Calendar event ID.

        Args:
            google_event_id: Google Calendar event ID

        Returns:
            SyncState if found, None otherwise
        """
        await self.ensure_indexes()

        doc = await self.collection.find_one({"google_event_id": google_event_id})
        if doc:
            doc.pop("_id", None)
            return SyncState(**doc)
        return None

    async def record_sync_state(
        self,
        user_id: str,
        persona_id: str | None,
        external_id: str,
        google_event_id: str,
        calendar_id: str = "primary",
        source_system: str = "manual",
        event_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SyncState:
        """
        Record a new sync state.

        Args:
            user_id: User who owns the sync state
            persona_id: Persona ID (can be None)
            external_id: External system's event identifier
            google_event_id: Google Calendar event ID
            calendar_id: Google Calendar ID
            source_system: Name of the source system
            event_hash: Hash of event data for change detection
            metadata: Additional metadata to store

        Returns:
            The created SyncState
        """
        await self.ensure_indexes()

        now = datetime.utcnow()
        state = SyncState(
            external_id=external_id,
            google_event_id=google_event_id,
            user_id=user_id,
            persona_id=persona_id,
            calendar_id=calendar_id,
            source_system=source_system,
            synced_at=now,
            event_hash=event_hash,
            metadata=metadata or {},
        )

        await self.collection.insert_one(state.model_dump())

        logger.info(
            "sync_state_recorded",
            extra={
                "user_id": user_id,
                "external_id": external_id,
                "google_event_id": google_event_id,
            },
        )

        return state

    async def update_sync_state(
        self,
        user_id: str,
        persona_id: str | None,
        external_id: str,
        google_event_id: str | None = None,
        event_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update an existing sync state.

        Args:
            user_id: User who owns the sync state
            persona_id: Persona ID (can be None)
            external_id: External system's event identifier
            google_event_id: New Google Calendar event ID (optional)
            event_hash: New event hash (optional)
            metadata: Metadata to merge (optional)

        Returns:
            True if updated, False if not found
        """
        await self.ensure_indexes()

        query = {
            "user_id": user_id,
            "external_id": external_id,
        }
        if persona_id:
            query["persona_id"] = persona_id
        else:
            query["persona_id"] = None

        update: dict[str, Any] = {"$set": {"synced_at": datetime.utcnow()}}

        if google_event_id is not None:
            update["$set"]["google_event_id"] = google_event_id
        if event_hash is not None:
            update["$set"]["event_hash"] = event_hash
        if metadata is not None:
            for key, value in metadata.items():
                update["$set"][f"metadata.{key}"] = value

        result = await self.collection.update_one(query, update)

        if result.modified_count > 0:
            logger.info(
                "sync_state_updated",
                extra={"user_id": user_id, "external_id": external_id},
            )
            return True
        return False

    async def delete_sync_state(
        self,
        user_id: str,
        persona_id: str | None,
        external_id: str,
    ) -> bool:
        """
        Delete a sync state.

        Args:
            user_id: User who owns the sync state
            persona_id: Persona ID (can be None)
            external_id: External system's event identifier

        Returns:
            True if deleted, False if not found
        """
        await self.ensure_indexes()

        query = {
            "user_id": user_id,
            "external_id": external_id,
        }
        if persona_id:
            query["persona_id"] = persona_id
        else:
            query["persona_id"] = None

        result = await self.collection.delete_one(query)

        if result.deleted_count > 0:
            logger.info(
                "sync_state_deleted",
                extra={"user_id": user_id, "external_id": external_id},
            )
            return True
        return False

    async def list_sync_states(
        self,
        user_id: str,
        persona_id: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[SyncState]:
        """
        List sync states for a user.

        Args:
            user_id: User who owns the sync states
            persona_id: Filter by persona ID (optional)
            limit: Maximum number of results
            skip: Number of results to skip

        Returns:
            List of SyncState objects
        """
        await self.ensure_indexes()

        query: dict[str, Any] = {"user_id": user_id}
        if persona_id is not None:
            query["persona_id"] = persona_id

        cursor = self.collection.find(query).sort("synced_at", -1).skip(skip).limit(limit)

        states = []
        async for doc in cursor:
            doc.pop("_id", None)
            states.append(SyncState(**doc))

        return states

    async def count_sync_states(
        self,
        user_id: str,
        persona_id: str | None = None,
    ) -> int:
        """
        Count sync states for a user.

        Args:
            user_id: User who owns the sync states
            persona_id: Filter by persona ID (optional)

        Returns:
            Count of sync states
        """
        await self.ensure_indexes()

        query: dict[str, Any] = {"user_id": user_id}
        if persona_id is not None:
            query["persona_id"] = persona_id

        return await self.collection.count_documents(query)


__all__ = ["MongoDBCalendarStore", "SyncState"]
