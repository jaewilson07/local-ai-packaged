"""Calendar agent for event scheduling and sync."""

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from src.capabilities.calendar.ai.dependencies import CalendarDeps
from src.shared.llm import get_llm_model


class CalendarState(BaseModel):
    """Shared state for calendar agents."""


# Create the calendar agent
calendar_agent = Agent(
    get_llm_model(),
    deps_type=CalendarDeps,
    system_prompt=(
        "You are an expert calendar and scheduling assistant. "
        "You help users create, update, and manage calendar events. "
        "Always provide clear confirmation of scheduling actions and handle timezone conversions."
    ),
)


@calendar_agent.tool
async def create_event(
    ctx: RunContext[CalendarDeps],
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """
    Create a new calendar event.

    This tool creates a new event in Google Calendar with the provided details.

    Args:
        ctx: Agent runtime context with dependencies
        summary: Event title/summary
        start: Start datetime (ISO format)
        end: End datetime (ISO format)
        description: Optional event description
        location: Optional event location

    Returns:
        String confirming event creation
    """
    # Import here to avoid circular dependencies
    from src.capabilities.calendar.calendar_sync.tools import create_event as _create

    deps = ctx.deps
    if not deps.db:
        await deps.initialize()

    from src.capabilities.calendar.schemas import CalendarEventData, CreateCalendarEventRequest

    event_data = CalendarEventData(
        summary=summary,
        description=description,
        location=location,
        start=start,
        end=end,
    )

    request = CreateCalendarEventRequest(
        user_id="system",
        persona_id="default",
        local_event_id=f"{summary}_{start}",
        event_data=event_data,
    )

    result = await _create(ctx, request)
    return f"Created event '{summary}' from {start} to {end}. Event ID: {result.event_id}"


@calendar_agent.tool
async def list_events(
    ctx: RunContext[CalendarDeps],
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """
    List calendar events in a time range.

    This tool retrieves calendar events within the specified time range.

    Args:
        ctx: Agent runtime context with dependencies
        start_time: Start time (ISO format, optional)
        end_time: End time (ISO format, optional)

    Returns:
        String describing the calendar events
    """
    # Import here to avoid circular dependencies
    from src.capabilities.calendar.calendar_sync.tools import list_events as _list

    deps = ctx.deps
    if not deps.db:
        await deps.initialize()

    from src.capabilities.calendar.schemas import ListCalendarEventsRequest

    request = ListCalendarEventsRequest(
        user_id="system",
        start_time=start_time,
        end_time=end_time,
    )

    result = await _list(ctx, request)
    return f"Found {result.count} events. Events: {result.events[:3]}"


__all__ = [
    "CalendarState",
    "calendar_agent",
    "create_event",
    "list_events",
]
