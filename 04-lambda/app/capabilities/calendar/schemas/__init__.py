"""Calendar capability schemas.

Pydantic models for calendar events, sync operations, and scheduling.
"""

from typing import Any

from pydantic import BaseModel, Field


class CalendarEventData(BaseModel):
    """Event data for calendar operations."""

    summary: str = Field(..., description="Event title/summary")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location")
    start: str = Field(..., description="Start datetime (ISO format)")
    end: str = Field(..., description="End datetime (ISO format)")
    timezone: str = Field("America/Los_Angeles", description="Timezone string")
    attendees: list[str] | None = Field(None, description="List of attendee emails")
    reminders: dict[str, Any] | None = Field(None, description="Reminder settings")


class CreateCalendarEventRequest(BaseModel):
    """Request to create a calendar event."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    local_event_id: str = Field(..., description="Unique local event identifier")
    event_data: CalendarEventData = Field(..., description="Event data")
    calendar_id: str | None = Field("primary", description="Google Calendar ID")


class UpdateCalendarEventRequest(BaseModel):
    """Request to update a calendar event."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    local_event_id: str = Field(..., description="Local event identifier")
    event_data: CalendarEventData = Field(..., description="Updated event data")
    calendar_id: str | None = Field("primary", description="Google Calendar ID")


class DeleteCalendarEventRequest(BaseModel):
    """Request to delete a calendar event."""

    user_id: str = Field(..., description="User ID")
    event_id: str = Field(..., description="Google Calendar event ID")
    calendar_id: str | None = Field("primary", description="Google Calendar ID")


class ListCalendarEventsRequest(BaseModel):
    """Request to list calendar events."""

    user_id: str = Field(..., description="User ID")
    calendar_id: str | None = Field("primary", description="Google Calendar ID")
    start_time: str | None = Field(None, description="Start time (ISO format)")
    end_time: str | None = Field(None, description="End time (ISO format)")
    timezone: str = Field("America/Los_Angeles", description="Timezone string")


class CalendarEventResponse(BaseModel):
    """Response from calendar operations."""

    success: bool
    message: str
    event_id: str | None = None
    local_event_id: str | None = None


class CalendarEventsListResponse(BaseModel):
    """Response with list of calendar events."""

    success: bool
    events: list[dict[str, Any]]
    count: int


class CalendarSyncResponse(BaseModel):
    """Response from calendar sync operation."""

    success: bool
    synced_count: int
    message: str


__all__ = [
    "CalendarEventData",
    "CalendarEventResponse",
    "CalendarEventsListResponse",
    "CalendarSyncResponse",
    "CreateCalendarEventRequest",
    "DeleteCalendarEventRequest",
    "ListCalendarEventsRequest",
    "UpdateCalendarEventRequest",
]
