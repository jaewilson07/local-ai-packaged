"""Calendar tools for Pydantic AI agent."""

import logging

from pydantic import Field

logger = logging.getLogger(__name__)


from server.projects.shared.wrappers import DepsWrapper  # noqa: E402


async def create_calendar_event(
    ctx: DepsWrapper,
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    local_event_id: str = Field(..., description="Unique local event identifier"),
    summary: str = Field(..., description="Event title/summary"),
    start: str = Field(..., description="Start datetime (ISO format)"),
    end: str = Field(..., description="End datetime (ISO format)"),
    description: str | None = Field(None, description="Event description"),
    location: str | None = Field(None, description="Event location"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
    attendees: list[str] | None = Field(None, description="List of attendee emails"),
) -> str:
    """
    Create a new calendar event in Google Calendar.

    Returns a JSON string with the result.
    """
    try:
        sync_service = ctx.sync_service

        event_data = {
            "summary": summary,
            "description": description or "",
            "location": location or "",
            "start": start,
            "end": end,
            "timezone": timezone,
        }

        if attendees:
            event_data["attendees"] = attendees

        result = await sync_service.sync_event_to_google_calendar(
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
            event_data=event_data,
            calendar_id=calendar_id,
        )

        if result.get("success"):
            return f"Event created successfully. Event ID: {result.get('gcal_event_id')}. {result.get('message', '')}"
        return f"Failed to create event: {result.get('message', 'Unknown error')}"

    except Exception as e:
        logger.exception("Error creating calendar event")
        return f"Error creating calendar event: {e!s}"


async def update_calendar_event(
    ctx: DepsWrapper,
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    local_event_id: str = Field(..., description="Local event identifier"),
    gcal_event_id: str = Field(..., description="Google Calendar event ID"),
    summary: str | None = Field(None, description="Event title/summary"),
    start: str | None = Field(None, description="Start datetime (ISO format)"),
    end: str | None = Field(None, description="End datetime (ISO format)"),
    description: str | None = Field(None, description="Event description"),
    location: str | None = Field(None, description="Event location"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
    attendees: list[str] | None = Field(None, description="List of attendee emails"),
) -> str:
    """
    Update an existing calendar event in Google Calendar.

    Returns a JSON string with the result.
    """
    try:
        sync_service = ctx.sync_service

        # Get existing event data if needed
        sync_state = await sync_service.get_sync_status(user_id, persona_id, local_event_id)
        existing_data = sync_state.get("event_data", {}) if sync_state else {}

        event_data = {
            "summary": summary or existing_data.get("summary", "Untitled Event"),
            "description": (
                description if description is not None else existing_data.get("description", "")
            ),
            "location": location if location is not None else existing_data.get("location", ""),
            "start": start or existing_data.get("start", ""),
            "end": end or existing_data.get("end", ""),
            "timezone": timezone,
        }

        if attendees is not None:
            event_data["attendees"] = attendees
        elif "attendees" in existing_data:
            event_data["attendees"] = existing_data["attendees"]

        updated_event = await sync_service.update_event(
            event_id=gcal_event_id,
            event_data=event_data,
            calendar_id=calendar_id,
            user_id=user_id,
            persona_id=persona_id,
            local_event_id=local_event_id,
        )

        return f"Event updated successfully. Event ID: {updated_event.get('id', gcal_event_id)}."

    except Exception as e:
        logger.exception("Error updating calendar event")
        return f"Error updating calendar event: {e!s}"


async def delete_calendar_event(
    ctx: DepsWrapper,
    user_id: str = Field(..., description="User ID"),
    event_id: str = Field(..., description="Google Calendar event ID"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
) -> str:
    """
    Delete a calendar event from Google Calendar.

    Returns a success message.
    """
    try:
        sync_service = ctx.sync_service

        success = await sync_service.delete_event(
            user_id=user_id,
            event_id=event_id,
            calendar_id=calendar_id,
        )

        if success:
            return f"Event {event_id} deleted successfully from Google Calendar."
        return f"Failed to delete event {event_id}."

    except Exception as e:
        logger.exception("Error deleting calendar event")
        return f"Error deleting calendar event: {e!s}"


async def list_calendar_events(
    ctx: DepsWrapper,
    user_id: str = Field(..., description="User ID"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
    start_time: str | None = Field(None, description="Start time (ISO format)"),
    end_time: str | None = Field(None, description="End time (ISO format)"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
) -> str:
    """
    List calendar events from Google Calendar.

    Returns a JSON string with the list of events.
    """
    try:
        sync_service = ctx.sync_service

        events = await sync_service.list_events(
            user_id=user_id,
            calendar_id=calendar_id,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
        )

        # Format events for response
        event_list = []
        for event in events:
            event_list.append(
                {
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "start": event.get("start", {}).get("dateTime")
                    or event.get("start", {}).get("date"),
                    "end": event.get("end", {}).get("dateTime") or event.get("end", {}).get("date"),
                    "location": event.get("location"),
                    "description": event.get("description"),
                    "htmlLink": event.get("htmlLink"),
                }
            )

        import json

        return json.dumps(
            {"success": True, "count": len(event_list), "events": event_list}, indent=2
        )

    except Exception as e:
        logger.exception("Error listing calendar events")
        return f"Error listing calendar events: {e!s}"
