"""Pydantic models for calendar operations."""

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

    success: bool = Field(..., description="Whether the operation was successful")
    gcal_event_id: str | None = Field(None, description="Google Calendar event ID")
    sync_status: str | None = Field(None, description="Sync status")
    message: str = Field(..., description="Status message")
    action: str | None = Field(None, description="Action taken: 'created', 'updated', or 'deleted'")
    html_link: str | None = Field(None, description="Google Calendar event HTML link")
    event_summary: str | None = Field(None, description="Event summary/title")
    event_start: str | None = Field(None, description="Event start time")
    event_end: str | None = Field(None, description="Event end time")


class CalendarEventsListResponse(BaseModel):
    """Response from list calendar events operation."""

    success: bool = Field(..., description="Whether the operation was successful")
    events: list[dict[str, Any]] = Field(
        default_factory=list, description="List of calendar events"
    )
    count: int = Field(0, description="Number of events returned")
