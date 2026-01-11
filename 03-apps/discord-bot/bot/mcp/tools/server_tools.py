"""Server information MCP tools."""

import logging

import discord

from bot.mcp.server import get_discord_client, mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def list_servers() -> list[dict]:
    """
    List all Discord servers (guilds) the bot is in.

    Returns:
        List of server information dictionaries with id, name, and member_count.
    """
    client = get_discord_client()
    servers = []
    for guild in client.guilds:
        servers.append(
            {
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
                "owner_id": str(guild.owner_id) if guild.owner_id else None,
                "icon_url": str(guild.icon.url) if guild.icon else None,
            }
        )
    return servers


@mcp.tool
async def get_server_info(server_id: str) -> dict:
    """
    Get detailed information about a Discord server.

    Args:
        server_id: The Discord server (guild) ID.

    Returns:
        Dictionary containing server details: name, member_count, channels, roles, etc.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    return {
        "id": str(guild.id),
        "name": guild.name,
        "member_count": guild.member_count,
        "owner_id": str(guild.owner_id) if guild.owner_id else None,
        "icon_url": str(guild.icon.url) if guild.icon else None,
        "description": guild.description,
        "created_at": guild.created_at.isoformat() if guild.created_at else None,
        "channel_count": len(guild.channels),
        "role_count": len(guild.roles),
    }


@mcp.tool
async def get_channels(server_id: str) -> list[dict]:
    """
    List all channels in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.

    Returns:
        List of channel information dictionaries.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    channels = []
    for channel in guild.channels:
        channel_info = {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "position": channel.position,
        }
        if hasattr(channel, "category") and channel.category:
            channel_info["category_id"] = str(channel.category.id)
            channel_info["category_name"] = channel.category.name
        channels.append(channel_info)

    return channels


@mcp.tool
async def list_members(server_id: str, limit: int = 100) -> list[dict]:
    """
    List members in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        limit: Maximum number of members to return (default: 100, max: 1000).

    Returns:
        List of member information dictionaries with id, username, roles, etc.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    # Limit to reasonable range
    limit = min(max(1, limit), 1000)

    members = []
    count = 0
    # Fetch members (Discord.py doesn't have fetch_members, use members list)
    for member in guild.members[:limit]:
        members.append(
            {
                "id": str(member.id),
                "username": member.name,
                "display_name": member.display_name,
                "roles": [
                    str(role.id) for role in member.roles if role.id != guild.id
                ],  # Exclude @everyone
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "bot": member.bot,
            }
        )
        count += 1

    return members


@mcp.tool
async def get_user_info(user_id: str) -> dict:
    """
    Get detailed information about a Discord user.

    Args:
        user_id: The Discord user ID.

    Returns:
        Dictionary containing user details: username, discriminator, avatar, etc.
    """
    client = get_discord_client()
    user = client.get_user(int(user_id))
    if not user:
        # Try fetching if not cached
        try:
            user = await client.fetch_user(int(user_id))
        except discord.NotFound:
            raise ValueError(f"User {user_id} not found")

    return {
        "id": str(user.id),
        "username": user.name,
        "discriminator": user.discriminator,
        "avatar_url": str(user.display_avatar.url) if user.display_avatar else None,
        "bot": user.bot,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
