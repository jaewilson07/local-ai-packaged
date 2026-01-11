"""MongoDB implementation of calendar sync state store."""

from typing import Optional, Dict, Any
import logging
from datetime import datetime
from pymongo.database import Database

from server.projects.shared.stores.base import BaseMongoStore

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
            name="user_persona_event_unique"
        )
        
        # Index for lookups by gcal_event_id
        self._create_index_safe(
            self.collection,
            [("gcal_event_id", ASCENDING)],
            name="gcal_event_id"
        )
        
        # Index for sync status queries
        self._create_index_safe(
            self.collection,
            [("sync_status", ASCENDING), ("last_sync_attempt", ASCENDING)],
            name="sync_status_attempt"
        )
    
    async def get_sync_state(
        self, user_id: str, persona_id: str, local_event_id: str
    ) -> Optional[Dict[str, Any]]:
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
            result = await self.collection.find_one({
                "user_id": user_id,
                "persona_id": persona_id,
                "local_event_id": local_event_id
            })
            return result
        except Exception as e:
            self._handle_operation_error("getting sync state", e, raise_on_error=False)
            return None
    
    async def save_sync_state(
        self,
        user_id: str,
        persona_id: str,
        local_event_id: str,
        gcal_event_id: Optional[str] = None,
        sync_status: str = "pending",
        event_data: Optional[Dict[str, Any]] = None,
        sync_error: Optional[str] = None,
        gcal_calendar_id: Optional[str] = None,
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
                await self.collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": sync_data}
                )
            else:
                # Insert new record
                sync_data["created_at"] = datetime.now().isoformat()
                await self.collection.insert_one(sync_data)
            
            logger.info(
                f"Saved sync state: {local_event_id} -> {gcal_event_id} ({sync_status})"
            )
        except Exception as e:
            self._handle_operation_error("saving sync state", e, raise_on_error=True)
