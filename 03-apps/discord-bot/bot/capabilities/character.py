"""
DEPRECATED: Monolithic character capability.

This module is deprecated. Character functionality has been split into:
    - bot.capabilities.character_commands.CharacterCommandsCapability (slash commands)
    - bot.capabilities.character_mention.CharacterMentionCapability (message handling)
    - bot.agents.character_engagement_agent.CharacterEngagementAgent (background engagement)

This file is kept for backward compatibility only.
"""

import asyncio
import logging
import re
import warnings

import discord
from discord import app_commands

from bot.api_client import APIClient
from bot.capabilities.base import BaseCapability
from bot.config import config

logger = logging.getLogger(__name__)

# Emit deprecation warning when module is imported
warnings.warn(
    "bot.capabilities.character.CharacterCapability is deprecated. "
    "Use CharacterCommandsCapability and CharacterMentionCapability instead.",
    DeprecationWarning,
    stacklevel=2,
)


class CharacterCapability(BaseCapability):
    """
    DEPRECATED: Monolithic character capability.

    This class is deprecated. Use the split capabilities instead:
    - CharacterCommandsCapability for slash commands
    - CharacterMentionCapability for message handling
    - CharacterEngagementAgent for background engagement

    Features:
    - Add/remove AI characters to channels
    - Characters respond when mentioned by name
    - Background engagement task for spontaneous interactions
    - Knowledge store queries via RAG
    """

    name = "character"
    description = "AI character interactions powered by Lambda API (DEPRECATED)"
    priority = 60  # After echo (50), before upload (100)

    def __init__(self, client: discord.Client, api_client: APIClient):
        """
        Initialize the character capability.

        Args:
            client: The Discord client instance
            api_client: The Lambda API client
        """
        warnings.warn(
            "CharacterCapability is deprecated. Use CharacterCommandsCapability "
            "and CharacterMentionCapability instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(client)
        self.api_client = api_client
        self.engagement_task: asyncio.Task | None = None
        self.engagement_running = False

        # Configuration
        self.engagement_check_interval = int(
            config.ENGAGEMENT_CHECK_INTERVAL if hasattr(config, "ENGAGEMENT_CHECK_INTERVAL") else 60
        )
        self.engagement_probability = float(
            config.ENGAGEMENT_PROBABILITY if hasattr(config, "ENGAGEMENT_PROBABILITY") else 0.15
        )

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Register character-related slash commands.
        """

        @tree.command(name="add_character", description="Add an AI character to this channel")
        @app_commands.describe(name="Character name (persona ID)")
        async def add_character_command(interaction: discord.Interaction, name: str):
            await self._handle_add_character(interaction, name)

        @tree.command(
            name="remove_character", description="Remove an AI character from this channel"
        )
        @app_commands.describe(name="Character name (persona ID)")
        async def remove_character_command(interaction: discord.Interaction, name: str):
            await self._handle_remove_character(interaction, name)

        @tree.command(
            name="list_characters", description="List all active characters in this channel"
        )
        async def list_characters_command(interaction: discord.Interaction):
            await self._handle_list_characters(interaction)

        @tree.command(
            name="clear_history", description="Clear conversation history for this channel"
        )
        @app_commands.describe(
            character="Optional: Character name to clear specific character history"
        )
        async def clear_history_command(interaction: discord.Interaction, character: str = None):
            await self._handle_clear_history(interaction, character)

        @tree.command(name="query_knowledge", description="Query the knowledge base using RAG")
        @app_commands.describe(query="Your question about the knowledge base")
        async def query_knowledge_command(interaction: discord.Interaction, query: str):
            await self._handle_query_knowledge(interaction, query)

        # Start engagement task
        self._start_engagement_task()

        logger.info("Character capability ready - commands registered (DEPRECATED)")

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
        """Remove character mentions from message content."""
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

    async def _handle_add_character(self, interaction: discord.Interaction, name: str):
        """Handle /add_character command."""
        await interaction.response.defer(ephemeral=True)

        try:
            channel_id = str(interaction.channel_id)
            result = await self.api_client.add_character(channel_id, name.lower(), name.lower())

            if result.get("success"):
                character = result.get("character", {})
                embed = discord.Embed(
                    title="Character Added",
                    description=f"**{character.get('name', name)}** has been added to this channel.",
                    color=discord.Color.green(),
                )
                if character.get("byline"):
                    embed.add_field(name="Description", value=character["byline"], inline=False)
                if character.get("profile_image"):
                    embed.set_thumbnail(url=character["profile_image"])

                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"Failed: {result.get('message', 'Could not add character')}", ephemeral=True
                )
        except Exception as e:
            logger.exception("Error in add_character")
            await interaction.followup.send(f"Error adding character: {e}", ephemeral=True)

    async def _handle_remove_character(self, interaction: discord.Interaction, name: str):
        """Handle /remove_character command."""
        await interaction.response.defer(ephemeral=True)

        try:
            channel_id = str(interaction.channel_id)
            result = await self.api_client.remove_character(channel_id, name.lower())

            if result.get("success"):
                await interaction.followup.send(
                    f"Character '{name}' removed from channel.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Failed: {result.get('message', 'Could not remove character')}", ephemeral=True
                )
        except Exception as e:
            logger.exception("Error in remove_character")
            await interaction.followup.send(f"Error removing character: {e}", ephemeral=True)

    async def _handle_list_characters(self, interaction: discord.Interaction):
        """Handle /list_characters command."""
        await interaction.response.defer()

        try:
            channel_id = str(interaction.channel_id)
            characters = await self.api_client.list_characters(channel_id)

            if not characters:
                embed = discord.Embed(
                    title="No Characters",
                    description="No characters are currently active in this channel.",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="Active Characters",
                description=f"{len(characters)} character(s) active in this channel:",
                color=discord.Color.blue(),
            )

            for char in characters:
                name = char.get("name") or char.get("character_id", "Unknown")
                byline = char.get("byline", "")
                embed.add_field(name=name, value=byline or "No description", inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.exception("Error in list_characters")
            await interaction.followup.send(f"Error listing characters: {e}", ephemeral=True)

    async def _handle_clear_history(self, interaction: discord.Interaction, character: str | None):
        """Handle /clear_history command."""
        await interaction.response.defer(ephemeral=True)

        try:
            channel_id = str(interaction.channel_id)
            character_id = character.lower() if character else None
            result = await self.api_client.clear_history(channel_id, character_id)

            if result.get("success"):
                await interaction.followup.send(
                    f"History cleared{' for ' + character if character else ''}.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Failed: {result.get('message', 'Could not clear history')}", ephemeral=True
                )
        except Exception as e:
            logger.exception("Error in clear_history")
            await interaction.followup.send(f"Error clearing history: {e}", ephemeral=True)

    async def _handle_query_knowledge(self, interaction: discord.Interaction, query: str):
        """Handle /query_knowledge command."""
        await interaction.response.defer()

        try:
            result = await self.api_client.query_knowledge_store(query)
            response_text = result.get("response", "No response received")

            # Discord has a 2000 character limit
            if len(response_text) <= 2000:
                await interaction.followup.send(response_text)
            else:
                chunks = [response_text[i : i + 2000] for i in range(0, len(response_text), 2000)]
                for chunk in chunks:
                    await interaction.followup.send(chunk)

        except Exception as e:
            logger.exception("Error querying knowledge store")
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    def _start_engagement_task(self):
        """Start the background engagement task."""
        if self.engagement_running:
            return
        self.engagement_running = True
        self.engagement_task = asyncio.create_task(self._engagement_loop())
        logger.info("Character engagement task started")

    async def _engagement_loop(self):
        """Background loop for spontaneous character engagement."""
        while self.engagement_running:
            try:
                await self._check_engagement_opportunities()
                await asyncio.sleep(self.engagement_check_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in engagement loop")
                await asyncio.sleep(self.engagement_check_interval)

    async def _check_engagement_opportunities(self):
        """Check channels for engagement opportunities."""
        try:
            for guild in self.client.guilds:
                for channel in guild.text_channels:
                    if not isinstance(channel, discord.TextChannel):
                        continue

                    try:
                        characters = await self.api_client.list_characters(str(channel.id))
                        if not characters:
                            continue

                        # Get recent messages
                        recent_messages = []
                        async for message in channel.history(limit=20):
                            if not message.author.bot and message.content:
                                recent_messages.append(message.content)

                        if len(recent_messages) < 3:
                            continue

                        # Check each character
                        for char in characters:
                            try:
                                result = await self.api_client.check_engagement(
                                    channel_id=str(channel.id),
                                    character_id=char.get("character_id"),
                                    recent_messages=recent_messages[-10:],
                                )

                                if result.get("should_engage") and result.get("response"):
                                    embed = discord.Embed(
                                        description=result["response"],
                                        color=discord.Color.green(),
                                    )
                                    character_name = char.get("name") or char.get(
                                        "character_id", "Character"
                                    )
                                    embed.set_author(
                                        name=character_name,
                                        icon_url=char.get("profile_image"),
                                    )
                                    await channel.send(embed=embed)
                                    logger.info(
                                        f"Character {char.get('character_id')} engaged in {channel.id}"
                                    )

                            except Exception as e:
                                logger.warning(f"Error checking engagement: {e}")

                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        logger.warning(f"Error checking channel {channel.id}: {e}")

        except Exception:
            logger.exception("Error in _check_engagement_opportunities")

    async def cleanup(self) -> None:
        """Stop engagement task and close API client."""
        self.engagement_running = False
        if self.engagement_task:
            self.engagement_task.cancel()
            try:
                await self.engagement_task
            except asyncio.CancelledError:
                pass

        await self.api_client.close()
        await super().cleanup()
