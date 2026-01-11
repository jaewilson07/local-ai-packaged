"""Handler for Discord message interactions."""

import logging
import re
from typing import Optional

import discord

from bot.api_client import APIClient

logger = logging.getLogger(__name__)


def extract_character_mentions(message: discord.Message) -> list[str]:
    """
    Extract character mentions from a message.

    Looks for patterns like @CharacterName or mentions of character names.
    """
    mentions = []
    message.content.lower()

    # Check for @mentions (though Discord mentions won't work for characters)
    # Instead, look for character name patterns
    # This is a simple implementation - could be enhanced with NLP

    # For now, we'll check if message mentions any known character names
    # In production, would query API for active characters in channel
    return mentions


async def handle_message(message: discord.Message, api_client: APIClient, client: discord.Client):
    """
    Handle incoming Discord messages.

    Checks for character mentions and generates responses.
    """
    try:
        channel_id = str(message.channel_id)
        user_id = str(message.author.id)

        # Get active characters in channel
        try:
            characters = await api_client.list_characters(channel_id)
        except Exception as e:
            logger.warning(f"Error listing characters: {e}")
            return

        if not characters:
            return  # No characters in channel

        # Check if message mentions any character
        message_lower = message.content.lower()
        mentioned_character: Optional[dict] = None

        for char in characters:
            character_name = (char.get("name") or char.get("character_id", "")).lower()
            character_id = char.get("character_id", "").lower()

            # Check if character name or ID is mentioned
            if character_name in message_lower or character_id in message_lower:
                # Check if it's a direct mention (starts with character name or @)
                if (
                    message_lower.startswith(character_name)
                    or message_lower.startswith(character_id)
                    or f"@{character_name}" in message_lower
                    or f"@{character_id}" in message_lower
                ):
                    mentioned_character = char
                    break

        if not mentioned_character:
            return  # No character mentioned

        # Generate response
        character_id = mentioned_character.get("character_id")
        character_name = mentioned_character.get("name") or character_id

        try:
            # Remove character mention from message for cleaner context
            clean_message = message.content
            for name_variant in [character_name, character_id]:
                # Remove @mentions
                clean_message = re.sub(
                    rf"@{re.escape(name_variant)}\s*,?\s*", "", clean_message, flags=re.IGNORECASE
                )
                # Remove name at start
                if clean_message.lower().startswith(name_variant.lower()):
                    clean_message = clean_message[len(name_variant) :].strip()
                    # Remove leading comma or colon
                    clean_message = clean_message.lstrip(",: ").strip()

            if not clean_message.strip():
                clean_message = message.content  # Fallback to original

            # Call API to generate response
            result = await api_client.chat(
                channel_id=channel_id,
                character_id=character_id,
                user_id=user_id,
                message=clean_message,
                message_id=str(message.id),
            )

            if result.get("success"):
                response_text = result.get("response", "")
                character_name = result.get("character_name") or character_name

                # Create embed for response
                embed = discord.Embed(description=response_text, color=discord.Color.blue())
                embed.set_author(
                    name=character_name, icon_url=mentioned_character.get("profile_image")
                )
                embed.set_footer(text=f"Responding to {message.author.display_name}")

                # Send response
                await message.channel.send(embed=embed)
            else:
                logger.warning(f"Failed to generate response: {result}")

        except Exception as e:
            logger.exception(f"Error generating character response: {e}")
            # Optionally send error message to user
            # await message.channel.send(f"❌ Error: {str(e)}")

    except Exception as e:
        logger.exception(f"Error handling message: {e}")
