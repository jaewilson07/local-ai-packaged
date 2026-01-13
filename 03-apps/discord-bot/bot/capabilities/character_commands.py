"""Character commands capability - handles character management slash commands."""

import logging

import discord
from discord import app_commands

from bot.api_client import APIClient
from bot.capabilities.base import BaseCapability

logger = logging.getLogger(__name__)


class CharacterCommandsCapability(BaseCapability):
    """
    Character commands capability that handles character management slash commands.

    Provides:
    - /add_character - Add an AI character to a channel
    - /remove_character - Remove an AI character from a channel
    - /list_characters - List active characters in a channel
    - /clear_history - Clear conversation history
    - /query_knowledge - Query the knowledge base using RAG
    """

    name = "character_commands"
    description = "Character management commands (add, remove, list)"
    priority = 65  # Before character_mention (60) to ensure commands are registered

    def __init__(
        self,
        client: discord.Client,
        api_client: APIClient,
        settings: dict | None = None,
    ):
        """
        Initialize the character commands capability.

        Args:
            client: The Discord client instance
            api_client: The Lambda API client for character management
            settings: Optional capability-specific settings from Lambda API
                - default_persona_id: Default persona to use when adding characters
        """
        super().__init__(client, settings=settings)
        self.api_client = api_client

        # Extract settings
        self.default_persona_id = self.settings.get("default_persona_id")

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """Register character management slash commands."""

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

        logger.info("Character commands capability ready - 5 commands registered")

    async def on_message(self, message: discord.Message) -> bool:
        """
        Character commands don't process messages.

        Returns:
            Always False - commands are handled via slash commands only
        """
        return False

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

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # API client cleanup is handled by the shared instance in main.py
        await super().cleanup()
