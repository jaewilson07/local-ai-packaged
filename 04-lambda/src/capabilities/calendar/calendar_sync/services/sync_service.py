"""Google Calendar sync service.

This module provides synchronization functionality between external systems
and Google Calendar, with sync state tracking to prevent duplicates.
"""

import hashlib
import json
import logging
from typing import Any

from services.external.google_calendar import (
    CalendarEvent,
    CalendarEventData,
    GoogleCalendarService,
)
from services.external.google_calendar.classes.exceptions import (
    GoogleCalendarNotFoundError,
)

logger = logging.getLogger(__name__)


class GoogleCalendarSyncService:
    """Service for synchronizing events with Google Calendar.

    Handles creating, updating, and deleting events while maintaining
    sync state to prevent duplicates and track changes.
    """

    def __init__(
        self,
        calendar_service: GoogleCalendarService,
        sync_store: Any,  # MongoDBCalendarStore - use Any to avoid circular import
        default_calendar_id: str = "primary",
    ):
        """
        Initialize the sync service.

        Args:
            calendar_service: Google Calendar service instance
            sync_store: MongoDB store for sync state
            default_calendar_id: Default calendar ID for operations
        """
        self.calendar = calendar_service
        self.sync_store = sync_store
        self.default_calendar_id = default_calendar_id

    @staticmethod
    def _compute_event_hash(event_data: CalendarEventData) -> str:
        """Compute a hash of event data for change detection."""
        data = {
            "summary": event_data.summary,
            "start": event_data.start,
            "end": event_data.end,
            "description": event_data.description,
            "location": event_data.location,
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    async def create_or_update_event(
        self,
        user_id: str,
        persona_id: str,
        external_id: str,
        event_data: CalendarEventData,
        calendar_id: str | None = None,
        source_system: str = "manual",
    ) -> dict[str, Any]:
        """
        Create or update an event with sync state tracking.

        If an event with the same external_id exists, it will be updated.
        Otherwise, a new event will be created.

        Args:
            user_id: User who owns the event
            persona_id: Persona ID (for multi-persona support)
            external_id: External system's event identifier
            event_data: Event data to sync
            calendar_id: Google Calendar ID (uses default if not provided)
            source_system: Name of the source system

        Returns:
            Dict with action taken ('created' or 'updated'), google_event_id, and event data
        """
        cal_id = calendar_id or self.default_calendar_id
        event_hash = self._compute_event_hash(event_data)

        # Check for existing sync state
        existing = await self.sync_store.get_by_external_id(
            user_id=user_id,
            persona_id=persona_id,
            external_id=external_id,
        )

        if existing:
            # Check if event actually changed
            if existing.event_hash == event_hash:
                logger.info(
                    "event_unchanged",
                    extra={"external_id": external_id, "google_event_id": existing.google_event_id},
                )
                return {
                    "action": "unchanged",
                    "google_event_id": existing.google_event_id,
                    "external_id": external_id,
                    "message": "Event unchanged",
                }

            # Update existing event
            try:
                event = await self.calendar.update_event(
                    event_id=existing.google_event_id,
                    event_data=event_data,
                    calendar_id=cal_id,
                )

                # Update sync state
                await self.sync_store.update_sync_state(
                    user_id=user_id,
                    persona_id=persona_id,
                    external_id=external_id,
                    google_event_id=existing.google_event_id,
                    event_hash=event_hash,
                )

                logger.info(
                    "event_updated",
                    extra={"external_id": external_id, "google_event_id": event.id},
                )

                return {
                    "action": "updated",
                    "google_event_id": event.id,
                    "external_id": external_id,
                    "event": event.model_dump(),
                }

            except GoogleCalendarNotFoundError:
                # Event was deleted in Google Calendar, recreate it
                logger.warning(
                    "event_not_found_recreating",
                    extra={"external_id": external_id, "google_event_id": existing.google_event_id},
                )
                # Fall through to create new event
                await self.sync_store.delete_sync_state(
                    user_id=user_id,
                    persona_id=persona_id,
                    external_id=external_id,
                )

        # Create new event
        event = await self.calendar.create_event(
            event_data=event_data,
            calendar_id=cal_id,
        )

        # Record sync state
        await self.sync_store.record_sync_state(
            user_id=user_id,
            persona_id=persona_id,
            external_id=external_id,
            google_event_id=event.id,
            calendar_id=cal_id,
            source_system=source_system,
            event_hash=event_hash,
        )

        logger.info(
            "event_created",
            extra={"external_id": external_id, "google_event_id": event.id},
        )

        return {
            "action": "created",
            "google_event_id": event.id,
            "external_id": external_id,
            "event": event.model_dump(),
        }

    async def delete_event(
        self,
        user_id: str,
        persona_id: str | None,
        event_id: str,
        calendar_id: str | None = None,
        is_google_event_id: bool = True,
    ) -> dict[str, Any]:
        """
        Delete an event from Google Calendar.

        Args:
            user_id: User who owns the event
            persona_id: Persona ID (for multi-persona support)
            event_id: Event ID (Google Calendar ID or external ID)
            calendar_id: Google Calendar ID (uses default if not provided)
            is_google_event_id: Whether event_id is a Google Calendar event ID

        Returns:
            Dict with action and status
        """
        cal_id = calendar_id or self.default_calendar_id

        google_event_id = event_id
        external_id = None

        # If it's an external ID, look up the Google event ID
        if not is_google_event_id:
            external_id = event_id
            sync_state = await self.sync_store.get_by_external_id(
                user_id=user_id,
                persona_id=persona_id,
                external_id=external_id,
            )
            if not sync_state:
                return {
                    "action": "not_found",
                    "message": f"No sync state found for external_id: {external_id}",
                }
            google_event_id = sync_state.google_event_id

        try:
            await self.calendar.delete_event(
                event_id=google_event_id,
                calendar_id=cal_id,
            )

            # Remove sync state if we have external_id
            if external_id:
                await self.sync_store.delete_sync_state(
                    user_id=user_id,
                    persona_id=persona_id,
                    external_id=external_id,
                )

            logger.info(
                "event_deleted",
                extra={"google_event_id": google_event_id, "external_id": external_id},
            )

            return {
                "action": "deleted",
                "google_event_id": google_event_id,
                "external_id": external_id,
            }

        except GoogleCalendarNotFoundError:
            # Event already deleted, just clean up sync state
            if external_id:
                await self.sync_store.delete_sync_state(
                    user_id=user_id,
                    persona_id=persona_id,
                    external_id=external_id,
                )
            return {
                "action": "already_deleted",
                "google_event_id": google_event_id,
                "external_id": external_id,
            }

    async def list_events(
        self,
        user_id: str,
        calendar_id: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        """
        List events from Google Calendar.

        Args:
            user_id: User making the request (for logging)
            calendar_id: Google Calendar ID (uses default if not provided)
            time_min: Start of time range (ISO format)
            time_max: End of time range (ISO format)
            max_results: Maximum number of events

        Returns:
            List of CalendarEvent objects
        """
        cal_id = calendar_id or self.default_calendar_id

        events = await self.calendar.list_events(
            calendar_id=cal_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
        )

        logger.info(
            "events_listed",
            extra={"user_id": user_id, "count": len(events), "calendar_id": cal_id},
        )

        return events

    async def get_sync_state(
        self,
        user_id: str,
        persona_id: str | None = None,
        external_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get sync state for an event.

        Args:
            user_id: User who owns the sync state
            persona_id: Persona ID (optional)
            external_id: External event ID (optional, returns all if not provided)

        Returns:
            Sync state data or None if not found
        """
        if external_id:
            state = await self.sync_store.get_by_external_id(
                user_id=user_id,
                persona_id=persona_id,
                external_id=external_id,
            )
            return state.model_dump() if state else None
        states = await self.sync_store.list_sync_states(
            user_id=user_id,
            persona_id=persona_id,
        )
        return [s.model_dump() for s in states]


__all__ = ["GoogleCalendarSyncService"]
