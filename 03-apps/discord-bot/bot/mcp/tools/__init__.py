"""MCP tool implementations for Discord bot."""

# Import mcp instance first
from bot.mcp.server import mcp

# Import tool modules (tools are registered via @mcp.tool decorators when imported)
from . import server_tools  # noqa: F401
from . import message_tools  # noqa: F401
from . import channel_tools  # noqa: F401
from . import event_tools  # noqa: F401
from . import role_tools  # noqa: F401
from . import agent_tools  # noqa: F401
from . import bluesky_tools  # noqa: F401
from . import tumblr_tools  # noqa: F401
from . import supabase_event_tools  # noqa: F401

__all__ = [
    "server_tools",
    "message_tools",
    "channel_tools",
    "event_tools",
    "role_tools",
    "agent_tools",
    "bluesky_tools",
    "tumblr_tools",
    "supabase_event_tools",
]
