"""Calendar Sync module.

Provides Google Calendar integration with sync state tracking.

Example usage:
    from capabilities.calendar.calendar_sync.services import GoogleCalendarSyncService
    from capabilities.calendar.calendar_sync.stores import MongoDBCalendarStore
    from capabilities.calendar.calendar_sync.tools import create_calendar_event
"""

# Export main components (lazy imports to avoid circular dependencies)
from .services import GoogleCalendarSyncService
from .stores import MongoDBCalendarStore, SyncState
from .tools import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    update_calendar_event,
)

__all__ = [
    # Services
    "GoogleCalendarSyncService",
    # Stores
    "MongoDBCalendarStore",
    "SyncState",
    # Tools
    "create_calendar_event",
    "update_calendar_event",
    "delete_calendar_event",
    "list_calendar_events",
]
