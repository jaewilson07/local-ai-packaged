"""Main Calendar agent implementation."""

from app.capabilities.calendar.calendar_sync.dependencies import CalendarDeps
from app.capabilities.calendar.calendar_sync.tools import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    update_calendar_event,
)
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from shared.llm import get_llm_model
from shared.wrappers import DepsWrapper


class CalendarState(BaseModel):
    """Minimal shared state for the Calendar agent."""


# System prompt for calendar agent
CALENDAR_SYSTEM_PROMPT = """You are a helpful calendar assistant that can manage Google Calendar events.

You can:
- Create new calendar events
- Update existing calendar events
- Delete calendar events
- List calendar events in a time range

When creating or updating events, make sure to:
- Provide clear, descriptive summaries/titles
- Include accurate start and end times in ISO format
- Include location if available
- Include description if helpful
- Use appropriate timezone (default: America/Los_Angeles)

Always confirm the operation result to the user.
"""


# Create the Calendar agent with AGUI support
calendar_agent = Agent(
    get_llm_model(), deps_type=CalendarDeps, system_prompt=CALENDAR_SYSTEM_PROMPT
)


# Register tools - create wrapper functions that bridge StateDeps to CalendarDeps
@calendar_agent.tool
async def create_calendar_event_tool(
    ctx: RunContext[CalendarDeps],
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
    """Create a new calendar event in Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    # Create a context wrapper for the calendar tools
    deps_ctx = DepsWrapper(deps)
    return await create_calendar_event(
        deps_ctx,
        user_id,
        persona_id,
        local_event_id,
        summary,
        start,
        end,
        description,
        location,
        timezone,
        calendar_id,
        attendees,
    )


@calendar_agent.tool
async def update_calendar_event_tool(
    ctx: RunContext[CalendarDeps],
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
    """Update an existing calendar event in Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    deps_ctx = DepsWrapper(deps)
    return await update_calendar_event(
        deps_ctx,
        user_id,
        persona_id,
        local_event_id,
        gcal_event_id,
        summary,
        start,
        end,
        description,
        location,
        timezone,
        calendar_id,
        attendees,
    )


@calendar_agent.tool
async def delete_calendar_event_tool(
    ctx: RunContext[CalendarDeps],
    user_id: str = Field(..., description="User ID"),
    event_id: str = Field(..., description="Google Calendar event ID"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
) -> str:
    """Delete a calendar event from Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    deps_ctx = DepsWrapper(deps)
    return await delete_calendar_event(deps_ctx, user_id, event_id, calendar_id)


@calendar_agent.tool
async def list_calendar_events_tool(
    ctx: RunContext[CalendarDeps],
    user_id: str = Field(..., description="User ID"),
    calendar_id: str | None = Field("primary", description="Google Calendar ID"),
    start_time: str | None = Field(None, description="Start time (ISO format)"),
    end_time: str | None = Field(None, description="End time (ISO format)"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
) -> str:
    """List calendar events from Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    deps_ctx = DepsWrapper(deps)
    return await list_calendar_events(
        deps_ctx, user_id, calendar_id, start_time, end_time, timezone
    )
