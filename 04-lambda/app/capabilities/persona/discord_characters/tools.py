"""Discord character management tools.

These are standalone tool functions that can be called directly
without an agent context. They manage Discord channel characters.
"""

import logging
from typing import Any

from app.capabilities.persona.discord_characters.config import config
from app.capabilities.persona.discord_characters.services_legacy import DiscordCharacterManager
from app.capabilities.persona.discord_characters.services_legacy.store import DiscordCharacterStore

logger = logging.getLogger(__name__)


async def _get_manager() -> DiscordCharacterManager:
    """Get a character manager instance."""
    store = DiscordCharacterStore(config.MONGODB_URI, config.MONGODB_DB_NAME)
    return DiscordCharacterManager(store)


async def add_discord_character_tool(
    channel_id: str, character_id: str, persona_id: str | None = None
) -> dict[str, Any]:
    """
    Add a character to a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier
        persona_id: Optional persona ID (defaults to character_id)

    Returns:
        Dictionary with success status and message.
    """
    try:
        manager = await _get_manager()
        await manager.add_character(channel_id, character_id, persona_id or character_id)
        return {
            "success": True,
            "message": f"Added character {character_id} to channel {channel_id}",
        }
    except Exception as e:
        logger.exception(f"Failed to add character: {e}")
        return {"success": False, "error": str(e)}


async def remove_discord_character_tool(channel_id: str, character_id: str) -> dict[str, Any]:
    """
    Remove a character from a Discord channel.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier

    Returns:
        Dictionary with success status and message.
    """
    try:
        manager = await _get_manager()
        await manager.remove_character(channel_id, character_id)
        return {
            "success": True,
            "message": f"Removed character {character_id} from channel {channel_id}",
        }
    except Exception as e:
        logger.exception(f"Failed to remove character: {e}")
        return {"success": False, "error": str(e)}


async def list_discord_characters_tool(channel_id: str) -> list[dict[str, Any]]:
    """
    List all characters in a Discord channel.

    Args:
        channel_id: Discord channel ID

    Returns:
        List of character dictionaries.
    """
    try:
        manager = await _get_manager()
        characters = await manager.list_characters(channel_id)
        return [
            {
                "channel_id": c.channel_id,
                "character_id": c.character_id,
                "persona_id": c.persona_id,
            }
            for c in characters
        ]
    except Exception as e:
        logger.exception(f"Failed to list characters: {e}")
        return []


async def clear_discord_history_tool(
    channel_id: str, character_id: str | None = None
) -> dict[str, Any]:
    """
    Clear conversation history for a channel or specific character.

    Args:
        channel_id: Discord channel ID
        character_id: Optional character ID to clear only that character's history

    Returns:
        Dictionary with success status and message.
    """
    try:
        manager = await _get_manager()
        if character_id:
            await manager.clear_history(channel_id, character_id)
            msg = f"Cleared history for character {character_id} in channel {channel_id}"
        else:
            await manager.clear_channel_history(channel_id)
            msg = f"Cleared all history for channel {channel_id}"
        return {"success": True, "message": msg}
    except Exception as e:
        logger.exception(f"Failed to clear history: {e}")
        return {"success": False, "error": str(e)}


async def chat_with_discord_character_tool(
    channel_id: str, character_id: str, user_id: str, message: str
) -> dict[str, Any]:
    """
    Generate a response from a character to a user message.

    Args:
        channel_id: Discord channel ID
        character_id: Character identifier
        user_id: User who sent the message
        message: Message content

    Returns:
        Dictionary with character response and metadata.
    """
    try:
        manager = await _get_manager()
        response = await manager.generate_response(channel_id, character_id, user_id, message)
        return {"success": True, "response": response}
    except Exception as e:
        logger.exception(f"Failed to generate response: {e}")
        return {"success": False, "error": str(e)}


__all__ = [
    "add_discord_character_tool",
    "chat_with_discord_character_tool",
    "clear_discord_history_tool",
    "list_discord_characters_tool",
    "remove_discord_character_tool",
]
