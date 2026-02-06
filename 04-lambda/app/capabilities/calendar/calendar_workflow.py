"""Calendar workflow - orchestration for event scheduling and sync."""

from app.capabilities.calendar.ai.dependencies import CalendarDeps
from app.capabilities.calendar.schemas import (
    CalendarEventResponse,
    CalendarEventsListResponse,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    ListCalendarEventsRequest,
    UpdateCalendarEventRequest,
)
from pydantic_ai import RunContext


async def create_event_workflow(
    request: CreateCalendarEventRequest,
    deps: CalendarDeps | None = None,
) -> CalendarEventResponse:
    """
    Execute calendar event creation workflow.

    Args:
        request: Create event request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Calendar event response
    """
    if deps is None:
        deps = CalendarDeps.from_settings()

    await deps.initialize()
    try:
        from capabilities.calendar.calendar_sync.tools import create_event

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await create_event(ctx, request)
        return result
    finally:
        await deps.cleanup()


async def update_event_workflow(
    request: UpdateCalendarEventRequest,
    deps: CalendarDeps | None = None,
) -> CalendarEventResponse:
    """
    Execute calendar event update workflow.

    Args:
        request: Update event request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Calendar event response
    """
    if deps is None:
        deps = CalendarDeps.from_settings()

    await deps.initialize()
    try:
        from capabilities.calendar.calendar_sync.tools import update_event

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await update_event(ctx, request)
        return result
    finally:
        await deps.cleanup()


async def delete_event_workflow(
    request: DeleteCalendarEventRequest,
    deps: CalendarDeps | None = None,
) -> CalendarEventResponse:
    """
    Execute calendar event deletion workflow.

    Args:
        request: Delete event request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Calendar event response
    """
    if deps is None:
        deps = CalendarDeps.from_settings()

    await deps.initialize()
    try:
        from capabilities.calendar.calendar_sync.tools import delete_event

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await delete_event(ctx, request)
        return result
    finally:
        await deps.cleanup()


async def list_events_workflow(
    request: ListCalendarEventsRequest,
    deps: CalendarDeps | None = None,
) -> CalendarEventsListResponse:
    """
    Execute calendar events listing workflow.

    Args:
        request: List events request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Calendar events list response
    """
    if deps is None:
        deps = CalendarDeps.from_settings()

    await deps.initialize()
    try:
        from capabilities.calendar.calendar_sync.tools import list_events

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await list_events(ctx, request)
        return result
    finally:
        await deps.cleanup()


__all__ = [
    "create_event_workflow",
    "delete_event_workflow",
    "list_events_workflow",
    "update_event_workflow",
]
