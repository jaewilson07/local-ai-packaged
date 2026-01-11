"""Main Calendar agent implementation."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import Optional, List
from pydantic_ai.ag_ui import StateDeps

from server.projects.shared.llm import get_llm_model
from server.projects.shared.wrappers import DepsWrapper
from server.projects.calendar.config import config
from server.projects.calendar.dependencies import CalendarDeps
from server.projects.calendar.tools import (
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    list_calendar_events,
)


class CalendarState(BaseModel):
    """Minimal shared state for the Calendar agent."""
    pass


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
    get_llm_model(),
    deps_type=CalendarDeps,
    system_prompt=CALENDAR_SYSTEM_PROMPT
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
    description: Optional[str] = Field(None, description="Event description"),
    location: Optional[str] = Field(None, description="Event location"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
    calendar_id: Optional[str] = Field("primary", description="Google Calendar ID"),
    attendees: Optional[List[str]] = Field(None, description="List of attendee emails"),
) -> str:
    """Create a new calendar event in Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    # Create a context wrapper for the calendar tools
    deps_ctx = DepsWrapper(deps)
    return await create_calendar_event(
        deps_ctx, user_id, persona_id, local_event_id, summary, start, end,
        description, location, timezone, calendar_id, attendees
    )


@calendar_agent.tool
async def update_calendar_event_tool(
    ctx: RunContext[CalendarDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    local_event_id: str = Field(..., description="Local event identifier"),
    gcal_event_id: str = Field(..., description="Google Calendar event ID"),
    summary: Optional[str] = Field(None, description="Event title/summary"),
    start: Optional[str] = Field(None, description="Start datetime (ISO format)"),
    end: Optional[str] = Field(None, description="End datetime (ISO format)"),
    description: Optional[str] = Field(None, description="Event description"),
    location: Optional[str] = Field(None, description="Event location"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
    calendar_id: Optional[str] = Field("primary", description="Google Calendar ID"),
    attendees: Optional[List[str]] = Field(None, description="List of attendee emails"),
) -> str:
    """Update an existing calendar event in Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    deps_ctx = DepsWrapper(deps)
    return await update_calendar_event(
        deps_ctx, user_id, persona_id, local_event_id, gcal_event_id,
        summary, start, end, description, location, timezone, calendar_id, attendees
    )


@calendar_agent.tool
async def delete_calendar_event_tool(
    ctx: RunContext[CalendarDeps],
    user_id: str = Field(..., description="User ID"),
    event_id: str = Field(..., description="Google Calendar event ID"),
    calendar_id: Optional[str] = Field("primary", description="Google Calendar ID"),
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
    calendar_id: Optional[str] = Field("primary", description="Google Calendar ID"),
    start_time: Optional[str] = Field(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Field(None, description="End time (ISO format)"),
    timezone: str = Field("America/Los_Angeles", description="Timezone string"),
) -> str:
    """List calendar events from Google Calendar."""
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    deps_ctx = DepsWrapper(deps)
    return await list_calendar_events(
        deps_ctx, user_id, calendar_id, start_time, end_time, timezone
    )
