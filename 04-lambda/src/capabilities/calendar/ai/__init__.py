"""AI agents for calendar capability."""

# Export dependencies and agents
# These are safe because calendar_agent doesn't import from calendar_sync/__init__.py
from capabilities.calendar.ai.calendar_agent import (
    CalendarState,
    calendar_agent,
    create_event,
    list_events,
)
from capabilities.calendar.ai.dependencies import CalendarDeps

__all__ = [
    "CalendarDeps",
    "CalendarState",
    "calendar_agent",
    "create_event",
    "list_events",
]
