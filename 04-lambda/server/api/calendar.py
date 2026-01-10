"""Calendar project REST API."""

from fastapi import APIRouter, HTTPException
import logging

from server.projects.calendar.models import (
    CreateCalendarEventRequest,
    UpdateCalendarEventRequest,
    DeleteCalendarEventRequest,
    ListCalendarEventsRequest,
    CalendarEventResponse,
    CalendarEventsListResponse,
)
from server.projects.calendar.dependencies import CalendarDeps
from server.core.api_utils import with_dependencies

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=CalendarEventResponse)
@with_dependencies(CalendarDeps)
async def create_calendar_event_endpoint(
    request: CreateCalendarEventRequest,
    deps: CalendarDeps
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
@with_dependencies(CalendarDeps)
async def update_calendar_event_endpoint(
    request: UpdateCalendarEventRequest,
    deps: CalendarDeps
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
            detail=f"Event {request.local_event_id} not found in sync state. Create the event first."
        )
    
    gcal_event_id = sync_state.get("gcal_event_id")
    if not gcal_event_id:
        raise HTTPException(
            status_code=404,
            detail=f"Google Calendar event ID not found for {request.local_event_id}. The event may not have been synced yet."
        )
    
    event_data_dict = request.event_data.dict()
    result = await sync_service.update_event(
        user_id=request.user_id,
        persona_id=request.persona_id,
        local_event_id=request.local_event_id,
        gcal_event_id=gcal_event_id,
        event_data=event_data_dict,
        calendar_id=request.calendar_id,
    )
    
    return CalendarEventResponse(
        success=result.get("success", False),
        gcal_event_id=result.get("gcal_event_id"),
        sync_status=result.get("sync_status"),
        message=result.get("message", ""),
        action="updated" if result.get("success") else None,
        html_link=result.get("html_link"),
        event_summary=event_data_dict.get("summary"),
        event_start=event_data_dict.get("start"),
        event_end=event_data_dict.get("end"),
    )


@router.post("/delete", response_model=CalendarEventResponse)
@with_dependencies(CalendarDeps)
async def delete_calendar_event_endpoint(
    request: DeleteCalendarEventRequest,
    deps: CalendarDeps
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
    
    success = await sync_service.delete_event(
        user_id=request.user_id,
        event_id=request.event_id,
        calendar_id=request.calendar_id,
    )
    
    return CalendarEventResponse(
        success=success,
        gcal_event_id=request.event_id,
        sync_status="deleted" if success else "failed",
        message=f"Event {'deleted' if success else 'failed to delete'} successfully",
        action="deleted" if success else None,
    )


@router.get("/list", response_model=CalendarEventsListResponse)
@with_dependencies(CalendarDeps)
async def list_calendar_events_endpoint(
    user_id: str,
    calendar_id: str = "primary",
    start_time: str | None = None,
    end_time: str | None = None,
    timezone: str = "America/Los_Angeles",
    deps: CalendarDeps = None
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
    
    events = await sync_service.list_events(
        user_id=user_id,
        calendar_id=calendar_id,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
    )
    
    return CalendarEventsListResponse(
        success=True,
        events=events,
        count=len(events),
    )
