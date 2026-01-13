"""Character mention capability - handles character responses to mentions."""

import logging
import re

import discord
from discord import app_commands

from bot.api_client import APIClient
from bot.capabilities.base import BaseCapability

logger = logging.getLogger(__name__)


class CharacterMentionCapability(BaseCapability):
    """
    Character mention capability that handles messages mentioning AI characters.

    When a user mentions a character by name (e.g., "Luna, what do you think?"),
    this capability generates a response from that character using the Lambda API.

    Requires:
        - character_commands: To add/remove characters from channels
    """

    name = "character_mention"
    description = "AI character responses when mentioned by name"
    priority = 60  # After echo (50), before upload (100)
    requires = ["character_commands"]  # Needs character management commands

    def __init__(
        self,
        client: discord.Client,
        api_client: APIClient,
        settings: dict | None = None,
    ):
        """
        Initialize the character mention capability.

        Args:
            client: The Discord client instance
            api_client: The Lambda API client for chat
            settings: Optional capability-specific settings from Lambda API
        """
        super().__init__(client, settings=settings)
        self.api_client = api_client

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when bot is ready.

        This capability doesn't register commands - it only handles messages.
        """
        logger.info("Character mention capability ready - listening for character mentions")

    async def on_message(self, message: discord.Message) -> bool:
        """
        Handle messages that mention characters.

        Args:
            message: The Discord message

        Returns:
            True if a character was mentioned and responded
        """
        try:
            channel_id = str(message.channel.id)
            user_id = str(message.author.id)

            # Get active characters in channel
            try:
                characters = await self.api_client.list_characters(channel_id)
            except Exception as e:
                logger.debug(f"Error listing characters for channel {channel_id}: {e}")
                return False

            if not characters:
                return False

            # Check if message mentions any character
            message_lower = message.content.lower()
            mentioned_character: dict | None = None

            for char in characters:
                character_name = (char.get("name") or char.get("character_id", "")).lower()
                character_id = char.get("character_id", "").lower()

                # Check if character name or ID is mentioned at start or with @
                if (
                    message_lower.startswith(character_name)
                    or message_lower.startswith(character_id)
                    or f"@{character_name}" in message_lower
                    or f"@{character_id}" in message_lower
                ):
                    mentioned_character = char
                    break

            if not mentioned_character:
                return False

            # Generate response
            character_id = mentioned_character.get("character_id")
            character_name = mentioned_character.get("name") or character_id

            # Remove character mention from message for cleaner context
            clean_message = self._clean_message(message.content, character_name, character_id)

            if not clean_message.strip():
                clean_message = message.content

            # Call API to generate response
            result = await self.api_client.chat(
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

                await message.channel.send(embed=embed)
                return True
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Failed to generate response for character {character_id}: {error_msg}")
            return False

        except Exception:
            logger.exception("Error handling character message")
            return False

    def _clean_message(self, content: str, character_name: str, character_id: str) -> str:
        """
        Remove character mentions from message content.

        Args:
            content: Original message content
            character_name: The character's display name
            character_id: The character's ID

        Returns:
            Cleaned message content
        """
        clean_message = content
        for name_variant in [character_name, character_id]:
            # Remove @mentions
            clean_message = re.sub(
                rf"@{re.escape(name_variant)}\s*,?\s*", "", clean_message, flags=re.IGNORECASE
            )
            # Remove name at start
            if clean_message.lower().startswith(name_variant.lower()):
                clean_message = clean_message[len(name_variant) :].strip()
                clean_message = clean_message.lstrip(",: ").strip()
        return clean_message

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # API client cleanup is handled by the shared instance in main.py
        await super().cleanup()
