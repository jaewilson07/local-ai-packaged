"""Calendar capability REST API endpoints."""

import logging
from typing import Annotated

from app.capabilities.calendar.ai.dependencies import CalendarDeps
from app.capabilities.calendar.calendar_workflow import (
    create_event_workflow,
    delete_event_workflow,
    list_events_workflow,
    update_event_workflow,
)
from app.capabilities.calendar.schemas import (
    CalendarEventResponse,
    CalendarEventsListResponse,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    ListCalendarEventsRequest,
    UpdateCalendarEventRequest,
)
from fastapi import APIRouter, Depends, HTTPException

from shared.dependency_factory import create_dependency_factory

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities", "calendar"])
logger = logging.getLogger(__name__)

# Use dependency factory to create deps getter (eliminates boilerplate)
get_calendar_deps = create_dependency_factory(CalendarDeps)


@router.post("/calendar/create", response_model=CalendarEventResponse)
async def create_calendar_event_endpoint(
    request: CreateCalendarEventRequest,
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
) -> CalendarEventResponse:
    """
    Create a new calendar event in Google Calendar.

    This endpoint creates a new event in Google Calendar and tracks the sync state
    to prevent duplicates. The event is stored with a unique local_event_id that
    can be used for future updates or deletions.

    **Use Cases:**
    - Create calendar events from extracted data
    - Schedule events automatically
    - Sync events from other systems
    """
    try:
        result = await create_event_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to create calendar event")
        raise HTTPException(status_code=500, detail=f"Event creation failed: {e!s}") from e


@router.post("/calendar/update", response_model=CalendarEventResponse)
async def update_calendar_event_endpoint(
    request: UpdateCalendarEventRequest,
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
) -> CalendarEventResponse:
    """
    Update an existing calendar event in Google Calendar.

    This endpoint updates an existing event in Google Calendar. The event is identified
    by the local_event_id and event data is merged with existing event.
    """
    try:
        result = await update_event_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to update calendar event")
        raise HTTPException(status_code=500, detail=f"Event update failed: {e!s}") from e


@router.post("/calendar/delete", response_model=CalendarEventResponse)
async def delete_calendar_event_endpoint(
    request: DeleteCalendarEventRequest,
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
) -> CalendarEventResponse:
    """
    Delete a calendar event from Google Calendar.

    This endpoint deletes an event from Google Calendar. The event is identified
    by the Google Calendar event ID.

    **Use Cases:**
    - Cancel scheduled events
    - Remove events that are no longer needed
    - Clean up duplicate events
    """
    try:
        result = await delete_event_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to delete calendar event")
        raise HTTPException(status_code=500, detail=f"Event deletion failed: {e!s}") from e


@router.get("/calendar/list", response_model=CalendarEventsListResponse)
async def list_calendar_events_endpoint(
    user_id: str,
    deps: Annotated[CalendarDeps, Depends(get_calendar_deps)],
    calendar_id: str = "primary",
    start_time: str | None = None,
    end_time: str | None = None,
    timezone: str = "America/Los_Angeles",
) -> CalendarEventsListResponse:
    """
    List calendar events from Google Calendar.

    This endpoint retrieves a list of events from Google Calendar within a specified
    time range. If no time range is provided, it defaults to the next 30 days.

    **Use Cases:**
    - View upcoming events
    - Check calendar availability
    - List events in a specific time range
    """
    try:
        request = ListCalendarEventsRequest(
            user_id=user_id,
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
        )
        result = await list_events_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to list calendar events")
        raise HTTPException(status_code=500, detail=f"Event listing failed: {e!s}") from e


__all__ = [
    "get_calendar_deps",
    "router",
]
