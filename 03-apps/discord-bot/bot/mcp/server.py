"""FastMCP server for Discord bot.

This module provides MCP (Model Context Protocol) endpoints for programmatic
Discord access, enabling AI assistants and other MCP clients to interact with
Discord servers.
"""

import logging
from typing import Optional
import discord
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Discord Bot")

# Global Discord client (set by main.py)
_discord_client: Optional[discord.Client] = None


def set_discord_client(client: discord.Client) -> None:
    """Set the Discord client instance for MCP tools to use."""
    global _discord_client
    _discord_client = client
    logger.info("Discord client set for MCP server")


def get_discord_client() -> discord.Client:
    """Get the Discord client instance."""
    if _discord_client is None:
        raise RuntimeError("Discord client not initialized. Bot may not be ready yet.")
    return _discord_client


# Tools will be registered when bot.mcp.tools is imported
# This happens when main.py imports from bot.mcp.server
