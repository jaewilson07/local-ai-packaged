"""Calendar project REST API."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User
from server.projects.calendar.dependencies import CalendarDeps
from server.projects.calendar.models import (
    CalendarEventResponse,
    CalendarEventsListResponse,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    UpdateCalendarEventRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# FastAPI dependency function with yield pattern for resource cleanup
async def get_calendar_deps() -> AsyncGenerator[CalendarDeps, None]:
    """FastAPI dependency that yields CalendarDeps."""
    deps = CalendarDeps.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()


@router.post("/create", response_model=CalendarEventResponse)
async def create_calendar_event_endpoint(
    request: CreateCalendarEventRequest, deps: Annotated[CalendarDeps, Depends(get_calendar_deps)]
):
    """
    Create a new calendar event in Google Calendar.

    This endpoint creates a new event in Google Calendar and tracks the sync state
    to prevent duplicates. The event is stored with a unique local_event_id that
    can be used for future updates or deletions.

    **Use Cases:**
    - Create calendar events from extracted data
    - Schedule events automatically
    - Sync events from other systems

    **Request Body:**
    ```json
    {
        "user_id": "user123",
        "persona_id": "persona1",
        "local_event_id": "event_123",
        "event_data": {
            "summary": "Team Meeting",
            "start": "2024-01-15T10:00:00",
            "end": "2024-01-15T11:00:00",
            "location": "Conference Room A",
            "description": "Weekly team sync"
        },
        "calendar_id": "primary"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "gcal_event_id": "abc123...",
        "sync_status": "synced",
        "message": "Event created in Google Calendar",
        "action": "created",
        "html_link": "https://calendar.google.com/event?eid=...",
        "event_summary": "Team Meeting",
        "event_start": "2024-01-15T10:00:00",
        "event_end": "2024-01-15T11:00:00"
    }
    ```
    """
    sync_service = deps.get_sync_service()

    event_data_dict = request.event_data.dict()
    result = await sync_service.sync_event_to_google_calendar(
        user_id=request.user_id,
        persona_id=request.persona_id,
        local_event_id=request.local_event_id,
        event_data=event_data_dict,
        calendar_id=request.calendar_id,
    )

    return CalendarEventResponse(
        success=result.get("success", False),
        gcal_event_id=result.get("gcal_event_id"),
        sync_status=result.get("sync_status"),
        message=result.get("message", ""),
        action="created" if result.get("success") else None,
        html_link=result.get("html_link"),
        event_summary=event_data_dict.get("summary"),
        event_start=event_data_dict.get("start"),
        event_end=event_data_dict.get("end"),
    )


@router.post("/update", response_model=CalendarEventResponse)
async def update_calendar_event_endpoint(
    request: UpdateCalendarEventRequest, deps: Annotated[CalendarDeps, Depends(get_calendar_deps)]
):
    """
    Update an existing calendar event in Google Calendar.

    This endpoint updates an existing event in Google Calendar. The event is identified
    by the local_event_id and gcal_event_id. Only provided fields will be updated.

    **Use Cases:**
    - Update event details (time, location, description)
    - Modify event attendees
    - Change event title or description

    **Request Body:**
    ```json
    {
        "user_id": "user123",
        "persona_id": "persona1",
        "local_event_id": "event_123",
        "gcal_event_id": "abc123...",
        "event_data": {
            "summary": "Team Meeting - Updated",
            "start": "2024-01-15T11:00:00",
            "end": "2024-01-15T12:00:00",
            "location": "Conference Room B"
        },
        "calendar_id": "primary"
    }
    ```
    """
    sync_service = deps.get_sync_service()

    # Get existing event to merge with updates
    sync_state = await sync_service.get_sync_status(
        request.user_id, request.persona_id, request.local_event_id
    )

    if not sync_state:
        raise HTTPException(
            status_code=404,
            detail=f"Event {request.local_event_id} not found in sync state. Create the event first.",
        )

    gcal_event_id = sync_state.get("gcal_event_id")
    if not gcal_event_id:
        raise HTTPException(
            status_code=404,
            detail=f"Google Calendar event ID not found for {request.local_event_id}. The event may not have been synced yet.",
        )

    event_data_dict = request.event_data.dict()
    updated_event = await sync_service.update_event(
        event_id=gcal_event_id,
        event_data=event_data_dict,
        calendar_id=request.calendar_id,
        user_id=request.user_id,
        persona_id=request.persona_id,
        local_event_id=request.local_event_id,
    )

    return CalendarEventResponse(
        success=True,
        gcal_event_id=updated_event.get("id", gcal_event_id),
        sync_status="synced",
        message="Event updated successfully",
        action="updated",
        html_link=updated_event.get("htmlLink"),
        event_summary=event_data_dict.get("summary"),
        event_start=event_data_dict.get("start"),
        event_end=event_data_dict.get("end"),
    )


@router.post("/delete", response_model=CalendarEventResponse)
async def delete_calendar_event_endpoint(
    request: DeleteCalendarEventRequest, deps: Annotated[CalendarDeps, Depends(get_calendar_deps)]
):
    """
    Delete a calendar event from Google Calendar.

    This endpoint deletes an event from Google Calendar. The event is identified
    by the Google Calendar event ID.

    **Use Cases:**
    - Cancel scheduled events
    - Remove events that are no longer needed
    - Clean up duplicate events

    **Request Body:**
    ```json
    {
        "user_id": "user123",
        "event_id": "abc123...",
        "calendar_id": "primary"
    }
    ```
    """
    sync_service = deps.get_sync_service()

    try:
        await sync_service.delete_event(
            event_id=request.event_id,
            calendar_id=request.calendar_id,
        )
        success = True
    except Exception as e:
        logger.exception(f"Failed to delete event: {e}")
        success = False

    return CalendarEventResponse(
        success=success,
        gcal_event_id=request.event_id,
        sync_status="deleted" if success else "failed",
        message=f"Event {'deleted' if success else 'failed to delete'} successfully",
        action="deleted" if success else None,
    )


@router.get("/list", response_model=CalendarEventsListResponse)
async def list_calendar_events_endpoint(
    user_id: str,
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
    calendar_id: str = "primary",
    start_time: str | None = None,
    end_time: str | None = None,
    timezone: str = "America/Los_Angeles",
):
    """
    List calendar events from Google Calendar.

    This endpoint retrieves a list of events from Google Calendar within a specified
    time range. If no time range is provided, it defaults to the next 30 days.

    **Use Cases:**
    - View upcoming events
    - Check calendar availability
    - List events in a specific time range

    **Query Parameters:**
    - `user_id` (required): User ID
    - `calendar_id` (optional, default: "primary"): Google Calendar ID
    - `start_time` (optional): Start time in ISO format
    - `end_time` (optional): End time in ISO format
    - `timezone` (optional, default: "America/Los_Angeles"): Timezone string

    **Response:**
    ```json
    {
        "success": true,
        "events": [
            {
                "id": "abc123...",
                "summary": "Team Meeting",
                "start": "2024-01-15T10:00:00",
                "end": "2024-01-15T11:00:00",
                "location": "Conference Room A",
                "description": "Weekly team sync",
                "htmlLink": "https://calendar.google.com/event?eid=..."
            }
        ],
        "count": 1
    }
    ```
    """
    sync_service = deps.get_sync_service()

    # Parse time strings to datetime objects if provided
    from datetime import datetime

    time_min = None
    time_max = None
    if start_time:
        try:
            time_min = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except Exception:
            time_min = datetime.fromisoformat(start_time)
    if end_time:
        try:
            time_max = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except Exception:
            time_max = datetime.fromisoformat(end_time)

    events = await sync_service.list_events(
        time_min=time_min,
        time_max=time_max,
        max_results=100,  # Default max results
        calendar_id=calendar_id,
    )

    return CalendarEventsListResponse(
        success=True,
        events=events,
        count=len(events),
    )


@router.get("/count")
async def count_calendar_events_endpoint(
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
    user: User = Depends(get_current_user),
    calendar_id: str | None = Query(None, description="Filter by calendar ID"),
    persona_id: str | None = Query(None, description="Filter by persona ID"),
):
    """
    Get count of synced calendar events for the authenticated user.

    This endpoint returns the total number of synced calendar events and a breakdown
    by calendar ID. The user_id is automatically extracted from the authenticated user.

    **Use Cases:**
    - Check how many events are synced across all calendars
    - Get event counts per calendar
    - Monitor sync status

    **Query Parameters:**
    - `calendar_id` (optional): Filter by specific calendar ID
    - `persona_id` (optional): Filter by specific persona ID

    **Response:**
    ```json
    {
        "total_events": 42,
        "events_by_calendar": {
            "primary": 30,
            "work@group.calendar.google.com": 12
        },
        "calendars_count": 2
    }
    ```

    **Authentication:**
    - Requires Cloudflare Access JWT in `Cf-Access-Jwt-Assertion` header
    - Automatically filters by authenticated user's ID
    """
    sync_service = deps.get_sync_service()

    result = await sync_service.get_synced_events_count(
        user_id=str(user.id),
        persona_id=persona_id,
        calendar_id=calendar_id,
    )

    return result
