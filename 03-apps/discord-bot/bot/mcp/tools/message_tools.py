"""Message management MCP tools."""

import logging

import discord

from bot.mcp.server import get_discord_client, mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def send_message(channel_id: str, content: str) -> dict:
    """
    Send a message to a Discord channel.

    Args:
        channel_id: The Discord channel ID.
        content: The message content to send.

    Returns:
        Dictionary containing the sent message information.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    message = await channel.send(content)
    return {
        "id": str(message.id),
        "content": message.content,
        "channel_id": str(message.channel.id),
        "author_id": str(message.author.id),
        "timestamp": message.created_at.isoformat(),
    }


@mcp.tool
async def read_messages(channel_id: str, limit: int = 50) -> list[dict]:
    """
    Read recent message history from a Discord channel.

    Args:
        channel_id: The Discord channel ID.
        limit: Maximum number of messages to retrieve (default: 50, max: 100).

    Returns:
        List of message information dictionaries.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    limit = min(max(1, limit), 100)
    messages = []
    async for message in channel.history(limit=limit):
        messages.append(
            {
                "id": str(message.id),
                "content": message.content,
                "author_id": str(message.author.id),
                "author_username": message.author.name,
                "channel_id": str(message.channel.id),
                "timestamp": message.created_at.isoformat(),
                "attachments": [att.url for att in message.attachments],
            }
        )

    return messages


@mcp.tool
async def add_reaction(channel_id: str, message_id: str, emoji: str) -> dict:
    """
    Add a reaction emoji to a message.

    Args:
        channel_id: The Discord channel ID.
        message_id: The Discord message ID.
        emoji: The emoji to add (can be unicode emoji or custom emoji ID/name).

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    try:
        message = await channel.fetch_message(int(message_id))
        await message.add_reaction(emoji)
        return {"success": True, "message": f"Added reaction {emoji} to message {message_id}"}
    except discord.NotFound:
        raise ValueError(f"Message {message_id} not found")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to add reaction: {e}") from e


@mcp.tool
async def add_multiple_reactions(channel_id: str, message_id: str, emojis: list[str]) -> dict:
    """
    Add multiple reactions to a message.

    Args:
        channel_id: The Discord channel ID.
        message_id: The Discord message ID.
        emojis: List of emojis to add.

    Returns:
        Dictionary with success status and count of reactions added.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    try:
        message = await channel.fetch_message(int(message_id))
        added = 0
        for emoji in emojis:
            try:
                await message.add_reaction(emoji)
                added += 1
            except discord.HTTPException:
                logger.warning(f"Failed to add reaction {emoji}")
        return {"success": True, "added": added, "total": len(emojis)}
    except discord.NotFound:
        raise ValueError(f"Message {message_id} not found")


@mcp.tool
async def remove_reaction(
    channel_id: str, message_id: str, emoji: str, user_id: str | None = None
) -> dict:
    """
    Remove a reaction from a message.

    Args:
        channel_id: The Discord channel ID.
        message_id: The Discord message ID.
        emoji: The emoji to remove.
        user_id: Optional user ID to remove reaction from (default: bot's own reaction).

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    try:
        message = await channel.fetch_message(int(message_id))
        if user_id:
            user = client.get_user(int(user_id))
            if not user:
                user = await client.fetch_user(int(user_id))
            await message.remove_reaction(emoji, user)
        else:
            await message.remove_reaction(emoji, client.user)
        return {"success": True, "message": f"Removed reaction {emoji} from message {message_id}"}
    except discord.NotFound:
        raise ValueError(f"Message {message_id} not found")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to remove reaction: {e}") from e


@mcp.tool
async def edit_message(channel_id: str, message_id: str, content: str) -> dict:
    """
    Edit an existing message in a Discord channel.

    Args:
        channel_id: The Discord channel ID.
        message_id: The Discord message ID to edit.
        content: The new message content.

    Returns:
        Dictionary containing the edited message information.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    try:
        message = await channel.fetch_message(int(message_id))
        # Check if message was sent by the bot
        if message.author.id != client.user.id:
            raise RuntimeError("Can only edit messages sent by the bot")

        edited_message = await message.edit(content=content)
        return {
            "id": str(edited_message.id),
            "content": edited_message.content,
            "channel_id": str(edited_message.channel.id),
            "author_id": str(edited_message.author.id),
            "timestamp": edited_message.created_at.isoformat(),
            "edited_timestamp": (
                edited_message.edited_at.isoformat() if edited_message.edited_at else None
            ),
        }
    except discord.NotFound:
        raise ValueError(f"Message {message_id} not found")
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to edit this message")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to edit message: {e}") from e


@mcp.tool
async def moderate_message(
    channel_id: str, message_id: str, delete: bool = True, timeout_user: int | None = None
) -> dict:
    """
    Moderate a message by deleting it and optionally timing out the user.

    Args:
        channel_id: The Discord channel ID.
        message_id: The Discord message ID to moderate.
        delete: Whether to delete the message (default: True).
        timeout_user: Optional timeout duration in seconds for the message author.

    Returns:
        Dictionary with moderation actions taken.
    """
    client = get_discord_client()
    channel = client.get_channel(int(channel_id))
    if not channel:
        raise ValueError(f"Channel {channel_id} not found")

    if not isinstance(channel, discord.TextChannel):
        raise ValueError(f"Channel {channel_id} is not a text channel")

    try:
        message = await channel.fetch_message(int(message_id))
        actions = []

        if delete:
            await message.delete()
            actions.append("deleted")

        if timeout_user and message.author:
            member = channel.guild.get_member(message.author.id)
            if member:
                # Timeout the user (requires TIMEOUT_MEMBERS permission)
                await member.timeout_for(discord.timedelta(seconds=timeout_user))
                actions.append(f"timeout_{timeout_user}s")

        return {
            "success": True,
            "message_id": message_id,
            "actions": actions,
        }
    except discord.NotFound:
        raise ValueError(f"Message {message_id} not found")
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to moderate this message")
    except discord.HTTPException as e:
        raise RuntimeError(f"Moderation failed: {e}") from e
