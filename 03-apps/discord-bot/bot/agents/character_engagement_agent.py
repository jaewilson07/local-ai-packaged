"""Character engagement agent - handles spontaneous character interactions."""

import asyncio
import logging
from typing import Any

import discord

from bot.agents.base import BaseAgent
from bot.api_client import APIClient
from bot.config import config

logger = logging.getLogger(__name__)


class CharacterEngagementAgent(BaseAgent):
    """
    Agent that handles spontaneous character engagement in Discord channels.

    This agent periodically checks channels with active characters for
    engagement opportunities. When a character decides to engage based on
    recent conversation context, it sends a message to the channel.

    This is implemented as an Agent (not a Capability) because:
    - It performs background polling/scanning
    - It's not directly triggered by user messages
    - It manages its own task loop and timing
    """

    def __init__(
        self,
        api_client: APIClient,
        discord_channel_id: str | None = None,
        check_interval: int | None = None,
    ):
        """
        Initialize the character engagement agent.

        Args:
            api_client: The Lambda API client for checking engagement
            discord_channel_id: Optional Discord channel for status messages
            check_interval: Interval in seconds between engagement checks (default: 60)
        """
        super().__init__(
            agent_id="character-engagement",
            name="Character Engagement",
            description="Spontaneous AI character interactions",
            discord_channel_id=discord_channel_id,
        )
        self.api_client = api_client
        self.check_interval = check_interval or int(
            getattr(config, "ENGAGEMENT_CHECK_INTERVAL", 60)
        )
        self._discord_client: discord.Client | None = None
        self._engagement_task: asyncio.Task | None = None

    def set_discord_client(self, client: discord.Client) -> None:
        """
        Set the Discord client for sending messages.

        Args:
            client: The Discord client instance
        """
        self._discord_client = client

    async def on_start(self) -> None:
        """Start the engagement check loop."""
        if not self._discord_client:
            logger.warning("Character engagement agent started without Discord client")
            return

        self._engagement_task = asyncio.create_task(self._engagement_loop())
        logger.info(f"Character engagement agent started (interval: {self.check_interval}s)")

    async def on_stop(self) -> None:
        """Stop the engagement check loop."""
        if self._engagement_task:
            self._engagement_task.cancel()
            try:
                await self._engagement_task
            except asyncio.CancelledError:
                pass
        logger.info("Character engagement agent stopped")

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Process a manual engagement task.

        Args:
            task: Task with 'channel_id' and optional 'character_id'

        Returns:
            Result dictionary with engagement status
        """
        channel_id = task.get("channel_id")
        character_id = task.get("character_id")

        if not channel_id:
            return {"success": False, "error": "Missing channel_id"}

        try:
            result = await self._check_channel_engagement(channel_id, character_id)
            return {"success": True, "engaged": result}
        except Exception as e:
            logger.exception(f"Error processing engagement task: {e}")
            return {"success": False, "error": str(e)}

    async def _engagement_loop(self) -> None:
        """Background loop for periodic engagement checks."""
        while self._running:
            try:
                await self._check_all_channels()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in character engagement loop")
                await asyncio.sleep(self.check_interval)

    async def _check_all_channels(self) -> None:
        """Check all channels with active characters for engagement opportunities."""
        if not self._discord_client:
            return

        try:
            for guild in self._discord_client.guilds:
                for channel in guild.text_channels:
                    if not isinstance(channel, discord.TextChannel):
                        continue

                    try:
                        await self._check_channel_engagement(str(channel.id))
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        logger.warning(f"Error checking channel {channel.id}: {e}")

        except Exception:
            logger.exception("Error in _check_all_channels")

    async def _check_channel_engagement(
        self, channel_id: str, specific_character_id: str | None = None
    ) -> bool:
        """
        Check a specific channel for engagement opportunities.

        Args:
            channel_id: The Discord channel ID
            specific_character_id: Optional specific character to check

        Returns:
            True if any character engaged
        """
        if not self._discord_client:
            return False

        try:
            # Get active characters in channel
            characters = await self.api_client.list_characters(channel_id)
            if not characters:
                return False

            # Filter to specific character if requested
            if specific_character_id:
                characters = [
                    c for c in characters if c.get("character_id") == specific_character_id
                ]
                if not characters:
                    return False

            # Get the channel object
            channel = self._discord_client.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                return False

            # Get recent messages for context
            recent_messages = []
            async for message in channel.history(limit=20):
                if not message.author.bot and message.content:
                    recent_messages.append(message.content)

            if len(recent_messages) < 3:
                return False

            # Check each character for engagement opportunity
            engaged = False
            for char in characters:
                try:
                    result = await self.api_client.check_engagement(
                        channel_id=channel_id,
                        character_id=char.get("character_id"),
                        recent_messages=recent_messages[-10:],
                    )

                    if result.get("should_engage") and result.get("response"):
                        embed = discord.Embed(
                            description=result["response"],
                            color=discord.Color.green(),
                        )
                        character_name = char.get("name") or char.get("character_id", "Character")
                        embed.set_author(
                            name=character_name,
                            icon_url=char.get("profile_image"),
                        )
                        await channel.send(embed=embed)
                        logger.info(
                            f"Character {char.get('character_id')} engaged in channel {channel_id}"
                        )
                        engaged = True

                except Exception as e:
                    logger.warning(f"Error checking engagement for character: {e}")

            return engaged

        except Exception:
            logger.exception(f"Error checking channel {channel_id} for engagement")
            return False
