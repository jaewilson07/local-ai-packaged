"""Supabase event management MCP tools."""

import logging
from datetime import datetime
from typing import Any

from bot.agents import get_agent_manager
from bot.mcp.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def create_supabase_event(
    server_id: str,
    name: str,
    start_time: str,
    description: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """
    Create an event in Supabase via the Supabase event agent.

    Args:
        server_id: The Discord server ID.
        name: Event name.
        start_time: Event start time (ISO format string).
        description: Optional event description.
        end_time: Optional event end time (ISO format string).
        location: Optional event location.

    Returns:
        Dictionary with created event information.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("supabase-event")
    if not agent:
        raise RuntimeError("Supabase event agent not registered")

    if not agent.is_running:
        raise RuntimeError("Supabase event agent is not running")

    # Parse start_time
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Invalid start_time format: {start_time}. Use ISO format.")

    # Parse end_time if provided
    end_dt = None
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid end_time format: {end_time}. Use ISO format.")

    task = {
        "action": "create_event",
        "server_id": server_id,
        "name": name,
        "description": description,
        "start_time": start_dt,
        "end_time": end_dt,
        "location": location,
        "task_id": f"create_{id(name)}",
    }

    return await agent.process_task(task)


@mcp.tool
async def sync_event_to_discord(event_id: int) -> dict[str, Any]:
    """
    Sync an event from Supabase to Discord via the Supabase event agent.

    Args:
        event_id: The Supabase event ID to sync.

    Returns:
        Dictionary with sync result including Discord event ID.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("supabase-event")
    if not agent:
        raise RuntimeError("Supabase event agent not registered")

    if not agent.is_running:
        raise RuntimeError("Supabase event agent is not running")

    task = {
        "action": "sync_to_discord",
        "event_id": event_id,
        "task_id": f"sync_{event_id}",
    }

    return await agent.process_task(task)


@mcp.tool
async def list_supabase_events(server_id: str | None = None) -> dict[str, Any]:
    """
    List events from Supabase via the Supabase event agent.

    Args:
        server_id: Optional Discord server ID to filter events.

    Returns:
        Dictionary with list of events.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("supabase-event")
    if not agent:
        raise RuntimeError("Supabase event agent not registered")

    if not agent.is_running:
        raise RuntimeError("Supabase event agent is not running")

    task = {
        "action": "list_events",
        "server_id": server_id,
        "task_id": f"list_{id(server_id) if server_id else 'all'}",
    }

    return await agent.process_task(task)


@mcp.tool
async def get_supabase_event(event_id: int) -> dict[str, Any]:
    """
    Get a specific event from Supabase via the Supabase event agent.

    Args:
        event_id: The Supabase event ID.

    Returns:
        Dictionary with event information.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("supabase-event")
    if not agent:
        raise RuntimeError("Supabase event agent not registered")

    if not agent.is_running:
        raise RuntimeError("Supabase event agent is not running")

    task = {
        "action": "get_event",
        "event_id": event_id,
        "task_id": f"get_{event_id}",
    }

    return await agent.process_task(task)
