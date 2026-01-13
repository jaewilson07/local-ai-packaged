"""Channel management MCP tools."""

import logging

import discord

from bot.mcp.server import get_discord_client, mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def create_text_channel(server_id: str, name: str, category_id: str | None = None) -> dict:
    """
    Create a new text channel in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        name: The name for the new channel.
        category_id: Optional category ID to place the channel in.

    Returns:
        Dictionary containing the created channel information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    category = None
    if category_id:
        category = guild.get_channel(int(category_id))
        if not category or not isinstance(category, discord.CategoryChannel):
            raise ValueError(f"Category {category_id} not found")

    try:
        channel = await guild.create_text_channel(name, category=category)
        return {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "category_id": str(category.id) if category else None,
            "position": channel.position,
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to create channels")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to create channel: {e}") from e


@mcp.tool
async def delete_channel(channel_id: str) -> dict:
    """
    Delete a Discord channel.

    Args:
        channel_id: The Discord channel ID to delete.

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    try:
        await channel.delete()
        return {"success": True, "message": f"Deleted channel {channel_id}"}
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to delete this channel")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to delete channel: {e}") from e


@mcp.tool
async def create_category(server_id: str, name: str) -> dict:
    """
    Create a new category channel in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        name: The name for the new category.

    Returns:
        Dictionary containing the created category information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    try:
        category = await guild.create_category(name)
        return {
            "id": str(category.id),
            "name": category.name,
            "type": str(category.type),
            "position": category.position,
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to create categories")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to create category: {e}") from e


@mcp.tool
async def get_channel_info(channel_id: str) -> dict:
    """
    Get detailed information about a Discord channel.

    Args:
        channel_id: The Discord channel ID.

    Returns:
        Dictionary containing detailed channel information.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    info = {
        "id": str(channel.id),
        "name": channel.name,
        "type": str(channel.type),
        "guild_id": str(channel.guild.id) if hasattr(channel, "guild") and channel.guild else None,
    }

    # Add channel-specific information
    if isinstance(channel, discord.TextChannel):
        info.update(
            {
                "topic": channel.topic,
                "nsfw": channel.nsfw,
                "slowmode_delay": channel.slowmode_delay,
                "category_id": str(channel.category.id) if channel.category else None,
                "category_name": channel.category.name if channel.category else None,
                "position": channel.position,
                "created_at": channel.created_at.isoformat(),
            }
        )
    elif isinstance(channel, discord.VoiceChannel):
        info.update(
            {
                "bitrate": channel.bitrate,
                "user_limit": channel.user_limit,
                "category_id": str(channel.category.id) if channel.category else None,
                "category_name": channel.category.name if channel.category else None,
                "position": channel.position,
                "created_at": channel.created_at.isoformat(),
            }
        )
    elif isinstance(channel, discord.CategoryChannel):
        info.update(
            {
                "position": channel.position,
                "created_at": channel.created_at.isoformat(),
            }
        )

    return info


@mcp.tool
async def move_channel(
    channel_id: str, category_id: str | None = None, position: int | None = None
) -> dict:
    """
    Move a channel to a different category or change its position.

    Args:
        channel_id: The Discord channel ID to move.
        category_id: Optional category ID to move the channel to (None to remove from category).
        position: Optional position within the category.

    Returns:
        Dictionary with success status and updated channel information.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
        raise ValueError(f"Channel {channel_id} cannot be moved (must be text or voice channel)")

    category = None
    if category_id:
        category = channel.guild.get_channel(int(category_id))
        if not category or not isinstance(category, discord.CategoryChannel):
            raise ValueError(f"Category {category_id} not found")

    try:
        if category:
            await channel.edit(category=category, position=position)
        elif position is not None:
            await channel.edit(position=position)
        else:
            await channel.edit(category=None)

        return {
            "success": True,
            "channel_id": str(channel.id),
            "category_id": str(category.id) if category else None,
            "position": channel.position,
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to move this channel")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to move channel: {e}") from e
