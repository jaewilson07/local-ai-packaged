"""Pydantic models for Google Calendar service."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CalendarEventData(BaseModel):
    """Data for creating or updating a calendar event."""

    summary: str = Field(..., description="Event title/summary")
    start: str = Field(..., description="Start datetime (ISO format)")
    end: str = Field(..., description="End datetime (ISO format)")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location")
    timezone: str = Field("America/Los_Angeles", description="Timezone")
    attendees: list[str] | None = Field(None, description="Attendee email addresses")


class CalendarEvent(BaseModel):
    """A calendar event returned from Google Calendar API."""

    id: str = Field(..., description="Google Calendar event ID")
    summary: str = Field(..., description="Event title")
    start: str | None = Field(None, description="Start datetime")
    end: str | None = Field(None, description="End datetime")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location")
    status: str = Field("confirmed", description="Event status")
    html_link: str | None = Field(None, description="Link to event in Google Calendar")
    created: str | None = Field(None, description="Creation timestamp")
    updated: str | None = Field(None, description="Last update timestamp")
    creator: dict[str, Any] | None = Field(None, description="Event creator info")
    organizer: dict[str, Any] | None = Field(None, description="Event organizer info")
    attendees: list[dict[str, Any]] | None = Field(None, description="Event attendees")

    @classmethod
    def from_google_event(cls, event: dict[str, Any]) -> "CalendarEvent":
        """Create CalendarEvent from Google Calendar API response."""
        start = event.get("start", {})
        end = event.get("end", {})

        return cls(
            id=event["id"],
            summary=event.get("summary", ""),
            start=start.get("dateTime") or start.get("date"),
            end=end.get("dateTime") or end.get("date"),
            description=event.get("description"),
            location=event.get("location"),
            status=event.get("status", "confirmed"),
            html_link=event.get("htmlLink"),
            created=event.get("created"),
            updated=event.get("updated"),
            creator=event.get("creator"),
            organizer=event.get("organizer"),
            attendees=event.get("attendees"),
        )


class SyncState(BaseModel):
    """Tracks synchronization state between external systems and Google Calendar."""

    external_id: str = Field(..., description="External system's event identifier")
    google_event_id: str = Field(..., description="Google Calendar event ID")
    user_id: str = Field(..., description="User who owns this sync state")
    persona_id: str | None = Field(None, description="Persona ID if applicable")
    calendar_id: str = Field("primary", description="Google Calendar ID")
    source_system: str = Field("manual", description="Source system name")
    synced_at: datetime = Field(default_factory=datetime.utcnow, description="Last sync timestamp")
    event_hash: str | None = Field(None, description="Hash of event data for change detection")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SyncResult(BaseModel):
    """Result of a sync operation."""

    action: str = Field(..., description="Action taken: 'created', 'updated', or 'unchanged'")
    google_event_id: str = Field(..., description="Google Calendar event ID")
    external_id: str = Field(..., description="External event ID")
    event: CalendarEvent | None = Field(None, description="The synced event")
    message: str | None = Field(None, description="Additional message")


__all__ = [
    "CalendarEvent",
    "CalendarEventData",
    "SyncResult",
    "SyncState",
]
