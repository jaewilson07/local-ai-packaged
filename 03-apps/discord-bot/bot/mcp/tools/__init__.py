"""MCP tool implementations for Discord bot."""

# Import mcp instance first

# Import tool modules (tools are registered via @mcp.tool decorators when imported)
from . import (
    agent_tools,
    bluesky_tools,
    channel_tools,
    event_tools,
    message_tools,
    role_tools,
    server_tools,
    supabase_event_tools,
    tumblr_tools,
)

__all__ = [
    "agent_tools",
    "bluesky_tools",
    "channel_tools",
    "event_tools",
    "message_tools",
    "role_tools",
    "server_tools",
    "supabase_event_tools",
    "tumblr_tools",
]
