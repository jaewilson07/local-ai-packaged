"""Calendar sync tools for Pydantic AI agents.

This module provides calendar event management tools that integrate with
Google Calendar through the sync service, maintaining sync state to
prevent duplicates.
"""

import logging
from typing import Any

from app.services.external.google_calendar import (
    CalendarEventData,
)
from app.services.external.google_calendar.classes.exceptions import (
    GoogleCalendarAuthError,
    GoogleCalendarException,
)

from .services.sync_service import GoogleCalendarSyncService

logger = logging.getLogger(__name__)


def _get_sync_service(ctx: Any) -> GoogleCalendarSyncService | None:
    """
    Extract sync service from context.

    The context can be a RunContext with deps, a DepsWrapper, or a direct deps object.
    Returns None if calendar service is not configured.
    """
    deps = getattr(ctx, "deps", ctx)
    if hasattr(deps, "_deps"):
        deps = deps._deps

    # Check if we have the required components
    sync_service = getattr(deps, "sync_service", None)
    if sync_service:
        return sync_service

    # Try to construct from components
    calendar_service = getattr(deps, "calendar_service", None)
    sync_store = getattr(deps, "sync_store", None)

    if calendar_service and sync_store:
        return GoogleCalendarSyncService(
            calendar_service=calendar_service,
            sync_store=sync_store,
        )

    return None


async def create_calendar_event(
    ctx: Any,
    user_id: str,
    persona_id: str,
    local_event_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    timezone: str = "America/Los_Angeles",
    calendar_id: str | None = "primary",
    attendees: list[str] | None = None,
) -> str:
    """
    Create a calendar event in Google Calendar.

    Uses the sync service to create the event and track sync state,
    preventing duplicates if the same local_event_id is used again.

    Args:
        ctx: Pydantic AI context with dependencies
        user_id: User who owns the event
        persona_id: Persona ID for multi-persona support
        local_event_id: Local/external event identifier (for deduplication)
        summary: Event title
        start: Start datetime (ISO format)
        end: End datetime (ISO format)
        description: Event description (optional)
        location: Event location (optional)
        timezone: Timezone for the event
        calendar_id: Google Calendar ID (default: "primary")
        attendees: List of attendee email addresses (optional)

    Returns:
        String describing the result of the operation
    """
    sync_service = _get_sync_service(ctx)

    if not sync_service:
        return (
            "[Not Configured] Google Calendar integration is not configured. "
            "Set GOOGLE_CALENDAR_TOKEN and related environment variables."
        )

    try:
        event_data = CalendarEventData(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            timezone=timezone,
            attendees=attendees,
        )

        result = await sync_service.create_or_update_event(
            user_id=user_id,
            persona_id=persona_id,
            external_id=local_event_id,
            event_data=event_data,
            calendar_id=calendar_id or "primary",
            source_system="agent_tool",
        )

        action = result["action"]
        google_event_id = result["google_event_id"]

        if action == "created":
            return f"Created event '{summary}' (ID: {google_event_id})"
        if action == "updated":
            return f"Updated existing event '{summary}' (ID: {google_event_id})"
        return f"Event '{summary}' unchanged (ID: {google_event_id})"

    except GoogleCalendarAuthError as e:
        logger.error(f"Calendar auth error: {e}")
        return f"[Auth Error] Failed to authenticate with Google Calendar: {e}"
    except GoogleCalendarException as e:
        logger.error(f"Calendar error: {e}")
        return f"[Error] Failed to create calendar event: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error creating calendar event: {e}")
        return f"[Error] Unexpected error: {e}"


async def update_calendar_event(
    ctx: Any,
    user_id: str,
    persona_id: str,
    local_event_id: str,
    gcal_event_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    timezone: str = "America/Los_Angeles",
    calendar_id: str | None = "primary",
    attendees: list[str] | None = None,
) -> str:
    """
    Update an existing calendar event in Google Calendar.

    Args:
        ctx: Pydantic AI context with dependencies
        user_id: User who owns the event
        persona_id: Persona ID for multi-persona support
        local_event_id: Local/external event identifier
        gcal_event_id: Google Calendar event ID (ignored - uses local_event_id lookup)
        summary: New event title (optional)
        start: New start datetime (optional)
        end: New end datetime (optional)
        description: New description (optional)
        location: New location (optional)
        timezone: Timezone for datetime fields
        calendar_id: Google Calendar ID
        attendees: New list of attendee emails (optional)

    Returns:
        String describing the result of the operation
    """
    sync_service = _get_sync_service(ctx)

    if not sync_service:
        return (
            "[Not Configured] Google Calendar integration is not configured. "
            "Set GOOGLE_CALENDAR_TOKEN and related environment variables."
        )

    try:
        # Get existing event to merge updates
        existing = await sync_service.get_sync_state(
            user_id=user_id,
            persona_id=persona_id,
            external_id=local_event_id,
        )

        if not existing:
            return f"[Not Found] No event found with local ID: {local_event_id}"

        # Require start/end for updates (can't do partial updates easily)
        if not start or not end:
            return "[Error] start and end times are required for updates"

        event_data = CalendarEventData(
            summary=summary or "Untitled Event",
            start=start,
            end=end,
            description=description,
            location=location,
            timezone=timezone,
            attendees=attendees,
        )

        result = await sync_service.create_or_update_event(
            user_id=user_id,
            persona_id=persona_id,
            external_id=local_event_id,
            event_data=event_data,
            calendar_id=calendar_id or "primary",
        )

        return f"Updated event (ID: {result['google_event_id']})"

    except GoogleCalendarAuthError as e:
        logger.error(f"Calendar auth error: {e}")
        return f"[Auth Error] Failed to authenticate with Google Calendar: {e}"
    except GoogleCalendarException as e:
        logger.error(f"Calendar error: {e}")
        return f"[Error] Failed to update calendar event: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error updating calendar event: {e}")
        return f"[Error] Unexpected error: {e}"


async def delete_calendar_event(
    ctx: Any,
    user_id: str,
    event_id: str,
    calendar_id: str | None = "primary",
    persona_id: str | None = None,
) -> str:
    """
    Delete a calendar event from Google Calendar.

    Args:
        ctx: Pydantic AI context with dependencies
        user_id: User who owns the event
        event_id: Event ID (can be local_event_id or Google Calendar event ID)
        calendar_id: Google Calendar ID
        persona_id: Persona ID (optional)

    Returns:
        String describing the result of the operation
    """
    sync_service = _get_sync_service(ctx)

    if not sync_service:
        return (
            "[Not Configured] Google Calendar integration is not configured. "
            "Set GOOGLE_CALENDAR_TOKEN and related environment variables."
        )

    try:
        # First try as external ID
        result = await sync_service.delete_event(
            user_id=user_id,
            persona_id=persona_id,
            event_id=event_id,
            calendar_id=calendar_id or "primary",
            is_google_event_id=False,
        )

        if result["action"] == "not_found":
            # Try as Google event ID
            result = await sync_service.delete_event(
                user_id=user_id,
                persona_id=persona_id,
                event_id=event_id,
                calendar_id=calendar_id or "primary",
                is_google_event_id=True,
            )

        action = result["action"]
        if action == "deleted":
            return f"Deleted event (ID: {event_id})"
        if action == "already_deleted":
            return f"Event already deleted (ID: {event_id})"
        return f"[Not Found] Event not found: {event_id}"

    except GoogleCalendarAuthError as e:
        logger.error(f"Calendar auth error: {e}")
        return f"[Auth Error] Failed to authenticate with Google Calendar: {e}"
    except GoogleCalendarException as e:
        logger.error(f"Calendar error: {e}")
        return f"[Error] Failed to delete calendar event: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error deleting calendar event: {e}")
        return f"[Error] Unexpected error: {e}"


async def list_calendar_events(
    ctx: Any,
    user_id: str,
    calendar_id: str | None = "primary",
    start_time: str | None = None,
    end_time: str | None = None,
    timezone: str = "America/Los_Angeles",
    max_results: int = 10,
) -> str:
    """
    List calendar events from Google Calendar.

    Args:
        ctx: Pydantic AI context with dependencies
        user_id: User making the request
        calendar_id: Google Calendar ID
        start_time: Start of time range (ISO format)
        end_time: End of time range (ISO format)
        timezone: Timezone for filtering (not yet implemented)
        max_results: Maximum number of events to return

    Returns:
        String describing the events found
    """
    sync_service = _get_sync_service(ctx)

    if not sync_service:
        return (
            "[Not Configured] Google Calendar integration is not configured. "
            "Set GOOGLE_CALENDAR_TOKEN and related environment variables."
        )

    try:
        events = await sync_service.list_events(
            user_id=user_id,
            calendar_id=calendar_id or "primary",
            time_min=start_time,
            time_max=end_time,
            max_results=max_results,
        )

        if not events:
            return "No events found in the specified time range."

        # Format events for display
        lines = [f"Found {len(events)} event(s):"]
        for event in events:
            start = event.start or "No start time"
            lines.append(f"  - {event.summary} ({start}) [ID: {event.id}]")

        return "\n".join(lines)

    except GoogleCalendarAuthError as e:
        logger.error(f"Calendar auth error: {e}")
        return f"[Auth Error] Failed to authenticate with Google Calendar: {e}"
    except GoogleCalendarException as e:
        logger.error(f"Calendar error: {e}")
        return f"[Error] Failed to list calendar events: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error listing calendar events: {e}")
        return f"[Error] Unexpected error: {e}"


__all__ = [
    "create_calendar_event",
    "delete_calendar_event",
    "list_calendar_events",
    "update_calendar_event",
]
