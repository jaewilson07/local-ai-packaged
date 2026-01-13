"""Scheduled event management MCP tools."""

import logging
from datetime import datetime

import discord

from bot.mcp.server import get_discord_client, mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def create_scheduled_event(
    server_id: str,
    name: str,
    start_time: str,
    event_type: str = "external",
    description: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
    channel_id: str | None = None,
) -> dict:
    """
    Create a scheduled event in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        name: The event name.
        start_time: Start time in ISO format (e.g., "2024-01-01T12:00:00").
        event_type: Event type: "external", "voice", or "stage" (default: "external").
        description: Optional event description.
        end_time: Optional end time in ISO format.
        location: Optional location (required for external events).
        channel_id: Optional channel ID (required for voice/stage events).

    Returns:
        Dictionary containing the created event information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    # Parse start time
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Invalid start_time format: {start_time}. Use ISO format.")

    # Parse end time if provided
    end_dt = None
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid end_time format: {end_time}. Use ISO format.")

    # Map event type
    event_type_map = {
        "external": discord.ScheduledEventEntityType.external,
        "voice": discord.ScheduledEventEntityType.voice,
        "stage": discord.ScheduledEventEntityType.stage_instance,
    }

    if event_type not in event_type_map:
        raise ValueError(
            f"Invalid event_type: {event_type}. Must be 'external', 'voice', or 'stage'."
        )

    entity_type = event_type_map[event_type]

    # Get channel if needed
    channel = None
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

    # Validate requirements
    if event_type in ("voice", "stage") and not channel:
        raise ValueError(f"channel_id is required for {event_type} events")
    if event_type == "external" and not location:
        raise ValueError("location is required for external events")

    try:
        kwargs = {
            "name": name,
            "start_time": start_dt,
            "entity_type": entity_type,
        }
        if description:
            kwargs["description"] = description
        if end_dt:
            kwargs["end_time"] = end_dt
        if location:
            kwargs["location"] = location
        if channel:
            kwargs["channel"] = channel

        event = await guild.create_scheduled_event(**kwargs)

        return {
            "id": str(event.id),
            "name": event.name,
            "description": event.description,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "location": event.location,
            "event_type": event_type,
            "status": str(event.status),
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to create scheduled events")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to create scheduled event: {e}") from e


@mcp.tool
async def edit_scheduled_event(
    server_id: str,
    event_id: str,
    name: str | None = None,
    description: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location: str | None = None,
    status: str | None = None,
) -> dict:
    """
    Edit an existing scheduled event.

    Args:
        server_id: The Discord server (guild) ID.
        event_id: The scheduled event ID.
        name: Optional new event name.
        description: Optional new event description.
        start_time: Optional new start time in ISO format.
        end_time: Optional new end time in ISO format.
        location: Optional new location.
        status: Optional new status: "scheduled", "active", "completed", or "canceled".

    Returns:
        Dictionary containing the updated event information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    try:
        event = await guild.fetch_scheduled_event(int(event_id))
    except discord.NotFound:
        raise ValueError(f"Scheduled event {event_id} not found")

    kwargs = {}
    if name:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if start_time:
        try:
            kwargs["start_time"] = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid start_time format: {start_time}")
    if end_time:
        try:
            kwargs["end_time"] = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid end_time format: {end_time}")
    if location:
        kwargs["location"] = location
    if status:
        status_map = {
            "scheduled": discord.ScheduledEventStatus.scheduled,
            "active": discord.ScheduledEventStatus.active,
            "completed": discord.ScheduledEventStatus.completed,
            "canceled": discord.ScheduledEventStatus.canceled,
        }
        if status not in status_map:
            raise ValueError(
                f"Invalid status: {status}. Must be 'scheduled', 'active', 'completed', or 'canceled'."
            )
        kwargs["status"] = status_map[status]

    if not kwargs:
        raise ValueError("At least one field must be provided to edit")

    try:
        await event.edit(**kwargs)
        # Fetch updated event
        updated_event = await guild.fetch_scheduled_event(int(event_id))

        return {
            "id": str(updated_event.id),
            "name": updated_event.name,
            "description": updated_event.description,
            "start_time": (
                updated_event.start_time.isoformat() if updated_event.start_time else None
            ),
            "end_time": updated_event.end_time.isoformat() if updated_event.end_time else None,
            "location": updated_event.location,
            "status": str(updated_event.status),
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to edit this scheduled event")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to edit scheduled event: {e}") from e
