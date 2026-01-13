"""MongoDB implementation of calendar sync state store."""

import logging
from datetime import datetime
from typing import Any

from pymongo.database import Database
from src.shared.stores.base import BaseMongoStore

logger = logging.getLogger(__name__)


class MongoDBCalendarStore(BaseMongoStore):
    """
    MongoDB store for calendar sync state.

    Adapts MongoDB to the interface expected by GoogleCalendarSyncService.
    """

    def __init__(self, db: Database, collection_name: str = "calendar_sync_state"):
        """
        Initialize MongoDB calendar store.

        Args:
            db: MongoDB database instance
            collection_name: Name of the collection for sync state
        """
        super().__init__(db, collection_name=collection_name)
        self._create_indexes()

    def _create_indexes(self) -> None:
        """Create indexes for efficient queries."""
        from pymongo import ASCENDING

        # Index for lookups by user_id, persona_id, local_event_id
        self._create_index_safe(
            self.collection,
            [("user_id", ASCENDING), ("persona_id", ASCENDING), ("local_event_id", ASCENDING)],
            unique=True,
            name="user_persona_event_unique",
        )

        # Index for lookups by gcal_event_id
        self._create_index_safe(
            self.collection, [("gcal_event_id", ASCENDING)], name="gcal_event_id"
        )

        # Index for sync status queries
        self._create_index_safe(
            self.collection,
            [("sync_status", ASCENDING), ("last_sync_attempt", ASCENDING)],
            name="sync_status_attempt",
        )

    async def get_sync_state(
        self, user_id: str, persona_id: str, local_event_id: str
    ) -> dict[str, Any] | None:
        """
        Get sync state for a local event.

        Args:
            user_id: User ID
            persona_id: Persona ID
            local_event_id: Local event identifier

        Returns:
            Dict with sync state or None if not found
        """
        try:
            result = await self.collection.find_one(
                {"user_id": user_id, "persona_id": persona_id, "local_event_id": local_event_id}
            )
            return result
        except Exception as e:
            self._handle_operation_error("getting sync state", e, raise_on_error=False)
            return None

    async def save_sync_state(
        self,
        user_id: str,
        persona_id: str,
        local_event_id: str,
        gcal_event_id: str | None = None,
        sync_status: str = "pending",
        event_data: dict[str, Any] | None = None,
        sync_error: str | None = None,
        gcal_calendar_id: str | None = None,
    ) -> None:
        """
        Save sync state to database.

        Args:
            user_id: User ID
            persona_id: Persona ID
            local_event_id: Local event identifier
            gcal_event_id: Google Calendar event ID (if synced)
            sync_status: Status ('pending', 'synced', 'failed', 'skipped')
            event_data: Event data snapshot
            sync_error: Error message if sync failed
            gcal_calendar_id: Google Calendar ID where event is synced
        """
        try:
            # Extract event metadata
            event_summary = None
            event_start_time = None
            event_end_time = None
            event_location = None

            if event_data:
                event_summary = event_data.get("summary")
                event_location = event_data.get("location")

                # Parse start/end times
                start_time = event_data.get("start")
                end_time = event_data.get("end")

                if isinstance(start_time, str):
                    event_start_time = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    ).isoformat()
                elif isinstance(start_time, datetime):
                    event_start_time = start_time.isoformat()

                if isinstance(end_time, str):
                    event_end_time = datetime.fromisoformat(
                        end_time.replace("Z", "+00:00")
                    ).isoformat()
                elif isinstance(end_time, datetime):
                    event_end_time = end_time.isoformat()

            sync_data = {
                "user_id": user_id,
                "persona_id": persona_id,
                "local_event_id": local_event_id,
                "gcal_event_id": gcal_event_id,
                "gcal_calendar_id": gcal_calendar_id or "primary",
                "sync_status": sync_status,
                "event_summary": event_summary,
                "event_start_time": event_start_time,
                "event_end_time": event_end_time,
                "event_location": event_location,
                "event_data": event_data or {},
                "sync_error": sync_error,
                "last_sync_attempt": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            if sync_status == "synced":
                sync_data["last_synced_at"] = datetime.now().isoformat()

            # Check if sync state already exists
            existing = await self.get_sync_state(user_id, persona_id, local_event_id)

            if existing:
                # Update existing record
                await self.collection.update_one({"_id": existing["_id"]}, {"$set": sync_data})
            else:
                # Insert new record
                sync_data["created_at"] = datetime.now().isoformat()
                await self.collection.insert_one(sync_data)

            logger.info(f"Saved sync state: {local_event_id} -> {gcal_event_id} ({sync_status})")
        except Exception as e:
            self._handle_operation_error("saving sync state", e, raise_on_error=True)

    async def get_by_external_id(self, external_id: str) -> dict[str, Any] | None:
        """
        Get sync state by external ID (for backward compatibility).

        External ID format: "local:{local_event_id}"

        Note: This method doesn't have user_id/persona_id context, so it may
        return results from any user. Prefer using get_sync_state() with full context.

        Args:
            external_id: External identifier (e.g., "local:event_123")

        Returns:
            Dict with sync state or None if not found
        """
        try:
            # Extract local_event_id from external_id format "local:{local_event_id}"
            if external_id.startswith("local:"):
                local_event_id = external_id[6:]  # Remove "local:" prefix
                result = await self.collection.find_one({"local_event_id": local_event_id})
                return result
            # Try to find by external_id directly (if stored)
            result = await self.collection.find_one({"external_id": external_id})
            return result
        except Exception as e:
            self._handle_operation_error(
                "getting sync state by external_id", e, raise_on_error=False
            )
            return None

    async def record_sync_state(
        self,
        external_id: str,
        google_event_id: str,
        source_system: str = "local",
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        persona_id: str | None = None,
    ) -> None:
        """
        Record sync state using external_id format (for backward compatibility).

        This is a wrapper around save_sync_state() that extracts user_id/persona_id
        from metadata or requires them as parameters.

        Args:
            external_id: External identifier (e.g., "local:event_123")
            google_event_id: Google Calendar event ID
            source_system: Source system identifier (default: "local")
            metadata: Optional metadata dict (may contain user_id, persona_id, calendar_id, local_event_id)
            user_id: User ID (required if not in metadata)
            persona_id: Persona ID (required if not in metadata)
        """
        metadata = metadata or {}

        # Extract user_id and persona_id from metadata or parameters
        user_id = user_id or metadata.get("user_id")
        persona_id = persona_id or metadata.get("persona_id")

        if not user_id or not persona_id:
            raise ValueError(
                "user_id and persona_id must be provided either as parameters or in metadata"
            )

        # Extract local_event_id from external_id format "local:{local_event_id}"
        if external_id.startswith("local:"):
            local_event_id = external_id[6:]  # Remove "local:" prefix
        else:
            local_event_id = external_id

        # Extract calendar_id from metadata
        calendar_id = metadata.get("calendar_id", "primary")

        # Call save_sync_state with proper parameters
        await self.save_sync_state(
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
            gcal_event_id=google_event_id,
            sync_status="synced",
            gcal_calendar_id=calendar_id,
        )

    async def count_events_by_user(
        self,
        user_id: str,
        persona_id: str | None = None,
        calendar_id: str | None = None,
        sync_status: str | None = None,
    ) -> dict[str, Any]:
        """
        Count synced events for a user with optional filters.

        Args:
            user_id: User ID (required)
            persona_id: Optional persona ID filter
            calendar_id: Optional calendar ID filter
            sync_status: Optional sync status filter (e.g., "synced", "pending", "failed")

        Returns:
            Dict with:
            - total: Total count of events matching criteria
            - by_calendar: Dict mapping calendar_id to count
            - calendars_count: Number of unique calendars
        """
        try:
            # Build query filter
            query = {"user_id": user_id}

            if persona_id:
                query["persona_id"] = persona_id

            if calendar_id:
                query["gcal_calendar_id"] = calendar_id

            if sync_status:
                query["sync_status"] = sync_status

            # Get total count
            total = await self.collection.count_documents(query)

            # Get counts grouped by calendar_id
            pipeline = [
                {"$match": query},
                {"$group": {"_id": "$gcal_calendar_id", "count": {"$sum": 1}}},
            ]

            by_calendar = {}
            async for doc in self.collection.aggregate(pipeline):
                calendar_id_key = doc["_id"] or "primary"
                by_calendar[calendar_id_key] = doc["count"]

            calendars_count = len(by_calendar)

            return {"total": total, "by_calendar": by_calendar, "calendars_count": calendars_count}
        except Exception as e:
            self._handle_operation_error("counting events by user", e, raise_on_error=False)
            return {"total": 0, "by_calendar": {}, "calendars_count": 0}
