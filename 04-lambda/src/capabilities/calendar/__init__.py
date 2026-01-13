"""Calendar capability - Event scheduling and sync."""

from .ai import CalendarDeps, CalendarState, calendar_agent, create_event, list_events
from .calendar_workflow import (
    create_event_workflow,
    delete_event_workflow,
    list_events_workflow,
    update_event_workflow,
)
from .router import get_calendar_deps, router
from .schemas import (
    CalendarEventData,
    CalendarEventResponse,
    CalendarEventsListResponse,
    CalendarSyncResponse,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    ListCalendarEventsRequest,
    UpdateCalendarEventRequest,
)

__all__ = [
    # Router
    "router",
    "get_calendar_deps",
    # Workflows
    "create_event_workflow",
    "update_event_workflow",
    "delete_event_workflow",
    "list_events_workflow",
    # AI
    "CalendarDeps",
    "CalendarState",
    "calendar_agent",
    "create_event",
    "list_events",
    # Schemas
    "CalendarEventData",
    "CreateCalendarEventRequest",
    "UpdateCalendarEventRequest",
    "DeleteCalendarEventRequest",
    "ListCalendarEventsRequest",
    "CalendarEventResponse",
    "CalendarEventsListResponse",
    "CalendarSyncResponse",
]
