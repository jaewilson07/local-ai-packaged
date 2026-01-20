"""Tests for Calendar tools."""

from unittest.mock import AsyncMock

import pytest
from server.projects.calendar.dependencies import CalendarDeps
from server.projects.calendar.tools import (
    create_calendar_event,
    delete_calendar_event,
    list_calendar_events,
    update_calendar_event,
)
from server.projects.shared.wrappers import DepsWrapper


@pytest.fixture
def mock_calendar_deps():
    """Create mock CalendarDeps."""
    deps = CalendarDeps()
    deps.mongo_client = AsyncMock()
    deps.db = AsyncMock()
    deps.sync_service = AsyncMock()
    return deps


@pytest.fixture
def mock_calendar_ctx(mock_calendar_deps):
    """Create mock DepsWrapper for calendar tools."""
    return DepsWrapper(mock_calendar_deps)


@pytest.mark.asyncio
async def test_create_calendar_event_success(mock_calendar_ctx):
    """Test creating a calendar event successfully."""
    # Setup
    mock_calendar_ctx.sync_service.sync_event_to_google_calendar = AsyncMock(
        return_value={
            "success": True,
            "gcal_event_id": "test_event_123",
            "message": "Event created",
        }
    )

    # Execute
    result = await create_calendar_event(
        mock_calendar_ctx,
        user_id="user1",
        persona_id="persona1",
        local_event_id="local1",
        summary="Test Event",
        start="2024-01-01T10:00:00",
        end="2024-01-01T11:00:00",
    )

    # Assert
    assert "successfully" in result.lower()
    assert "test_event_123" in result
    mock_calendar_ctx.sync_service.sync_event_to_google_calendar.assert_called_once()


@pytest.mark.asyncio
async def test_create_calendar_event_failure(mock_calendar_ctx):
    """Test creating a calendar event with failure."""
    # Setup
    mock_calendar_ctx.sync_service.sync_event_to_google_calendar = AsyncMock(
        return_value={"success": False, "message": "Authentication failed"}
    )

    # Execute
    result = await create_calendar_event(
        mock_calendar_ctx,
        user_id="user1",
        persona_id="persona1",
        local_event_id="local1",
        summary="Test Event",
        start="2024-01-01T10:00:00",
        end="2024-01-01T11:00:00",
    )

    # Assert
    assert "failed" in result.lower()
    assert "Authentication failed" in result


@pytest.mark.asyncio
async def test_update_calendar_event_success(mock_calendar_ctx):
    """Test updating a calendar event successfully."""
    # Setup
    mock_calendar_ctx.sync_service.get_sync_status = AsyncMock(
        return_value={
            "event_data": {
                "summary": "Old Event",
                "description": "Old description",
                "start": "2024-01-01T10:00:00",
                "end": "2024-01-01T11:00:00",
            }
        }
    )
    mock_calendar_ctx.sync_service.sync_event_to_google_calendar = AsyncMock(
        return_value={
            "success": True,
            "gcal_event_id": "test_event_123",
            "message": "Event updated",
        }
    )

    # Execute
    result = await update_calendar_event(
        mock_calendar_ctx,
        user_id="user1",
        persona_id="persona1",
        local_event_id="local1",
        gcal_event_id="test_event_123",
        summary="Updated Event",
    )

    # Assert
    assert "successfully" in result.lower() or "updated" in result.lower()


@pytest.mark.asyncio
async def test_delete_calendar_event_success(mock_calendar_ctx):
    """Test deleting a calendar event successfully."""
    # Setup
    mock_calendar_ctx.sync_service.delete_event = AsyncMock(
        return_value={"success": True, "message": "Event deleted"}
    )

    # Execute
    result = await delete_calendar_event(
        mock_calendar_ctx,
        user_id="user1",
        event_id="test_event_123",
    )

    # Assert
    assert "successfully" in result.lower() or "deleted" in result.lower()
    mock_calendar_ctx.sync_service.delete_event.assert_called_once()


@pytest.mark.asyncio
async def test_list_calendar_events_success(mock_calendar_ctx):
    """Test listing calendar events successfully."""
    # Setup
    mock_events = [
        {
            "id": "event1",
            "summary": "Event 1",
            "start": {"dateTime": "2024-01-01T10:00:00"},
            "end": {"dateTime": "2024-01-01T11:00:00"},
        },
        {
            "id": "event2",
            "summary": "Event 2",
            "start": {"dateTime": "2024-01-02T10:00:00"},
            "end": {"dateTime": "2024-01-02T11:00:00"},
        },
    ]
    mock_calendar_ctx.sync_service.list_events = AsyncMock(return_value=mock_events)

    # Execute
    result = await list_calendar_events(
        mock_calendar_ctx,
        user_id="user1",
    )

    # Assert
    assert "event" in result.lower()
    mock_calendar_ctx.sync_service.list_events.assert_called_once()
