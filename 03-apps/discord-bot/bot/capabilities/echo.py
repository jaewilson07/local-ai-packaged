"""Echo capability - responds when the bot is @mentioned."""

import logging

import discord
from discord import app_commands

from bot.capabilities.base import BaseCapability

logger = logging.getLogger(__name__)


class EchoCapability(BaseCapability):
    """
    Echo capability that responds when the bot is @mentioned.

    This is a simple capability for testing that the bot is working.
    When a user @mentions the bot, it echoes back their message.
    """

    name = "echo"
    description = "Echoes messages when the bot is @mentioned"
    priority = 50  # Medium priority

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when bot is ready.

        The echo capability doesn't register any slash commands.
        """
        logger.info(f"Echo capability ready - will respond to @mentions of {self.client.user}")

    async def on_message(self, message: discord.Message) -> bool:
        """
        Handle incoming messages.

        Responds with an echo when the bot is @mentioned.

        Args:
            message: The Discord message

        Returns:
            True if the bot was mentioned and we responded
        """
        # Only respond if bot is mentioned
        if not self.is_bot_mentioned(message):
            return False

        # Don't respond to ourselves
        if message.author == self.client.user:
            return False

        # Don't respond to other bots
        if message.author.bot:
            return False

        # Get message content without the mention
        content = self.get_message_without_mention(message)

        # If there's no content after removing the mention, provide a default response
        if not content.strip():
            content = "(empty message)"

        # Create echo response
        echo_text = f"Echo: {content}"

        logger.info(
            f"Echoing message from {message.author.display_name} "
            f"in #{message.channel}: {content[:50]}..."
        )

        try:
            # Send echo response as a reply
            await message.channel.send(echo_text, reference=message)
            return True
        except discord.Forbidden:
            logger.error(f"Bot lacks permission to send messages in {message.channel}")
            return True  # Still return True since we "handled" it
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending echo response: {e}")
            return True
