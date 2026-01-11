"""Handler for Discord slash commands."""

import logging
from typing import List, Optional

import discord
from discord.ui import Button, View

from bot.api_client import APIClient

logger = logging.getLogger(__name__)


class CharacterSelectView(View):
    """View for selecting a character from search results."""

    def __init__(self, characters: List[dict], api_client: APIClient, channel_id: str):
        super().__init__(timeout=60.0)
        self.characters = characters
        self.api_client = api_client
        self.channel_id = channel_id

    @discord.ui.button(label="Add Character", style=discord.ButtonStyle.primary)
    async def add_button(self, interaction: discord.Interaction, button: Button):
        """Handle character selection."""
        await interaction.response.defer()
        # Character selection would be handled here
        # For now, we'll use the first character
        if self.characters:
            character = self.characters[0]
            try:
                result = await self.api_client.add_character(str(self.channel_id), character["id"])
                if result.get("success"):
                    await interaction.followup.send(
                        f"Character '{character['name']}' added to channel!", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"Failed to add character: {result.get('message', 'Unknown error')}",
                        ephemeral=True,
                    )
            except Exception as e:
                logger.exception(f"Error adding character: {e}")
                await interaction.followup.send(f"Error adding character: {str(e)}", ephemeral=True)


async def handle_add_character(interaction: discord.Interaction, name: str, api_client: APIClient):
    """Handle /add_character command."""
    await interaction.response.defer(ephemeral=True)

    try:
        channel_id = str(interaction.channel_id)
        result = await api_client.add_character(channel_id, name.lower(), name.lower())

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
                f"❌ {result.get('message', 'Failed to add character')}", ephemeral=True
            )
    except Exception as e:
        logger.exception(f"Error in add_character: {e}")
        await interaction.followup.send(f"❌ Error adding character: {str(e)}", ephemeral=True)


async def handle_remove_character(
    interaction: discord.Interaction, name: str, api_client: APIClient
):
    """Handle /remove_character command."""
    await interaction.response.defer(ephemeral=True)

    try:
        channel_id = str(interaction.channel_id)
        result = await api_client.remove_character(channel_id, name.lower())

        if result.get("success"):
            await interaction.followup.send(
                f"✅ {result.get('message', 'Character removed')}", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ {result.get('message', 'Failed to remove character')}", ephemeral=True
            )
    except Exception as e:
        logger.exception(f"Error in remove_character: {e}")
        await interaction.followup.send(f"❌ Error removing character: {str(e)}", ephemeral=True)


async def handle_list_characters(interaction: discord.Interaction, api_client: APIClient):
    """Handle /list_characters command."""
    await interaction.response.defer()

    try:
        channel_id = str(interaction.channel_id)
        characters = await api_client.list_characters(channel_id)

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
        logger.exception(f"Error in list_characters: {e}")
        await interaction.followup.send(f"❌ Error listing characters: {str(e)}", ephemeral=True)


async def handle_clear_history(
    interaction: discord.Interaction, character: Optional[str], api_client: APIClient
):
    """Handle /clear_history command."""
    await interaction.response.defer(ephemeral=True)

    try:
        channel_id = str(interaction.channel_id)
        character_id = character.lower() if character else None
        result = await api_client.clear_history(channel_id, character_id)

        if result.get("success"):
            await interaction.followup.send(
                f"✅ {result.get('message', 'History cleared')}", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ {result.get('message', 'Failed to clear history')}", ephemeral=True
            )
    except Exception as e:
        logger.exception(f"Error in clear_history: {e}")
        await interaction.followup.send(f"❌ Error clearing history: {str(e)}", ephemeral=True)


async def handle_query_knowledge_store(
    interaction: discord.Interaction, query: str, api_client: APIClient
):
    """Handle /query_knowledgestore command."""
    await interaction.response.defer()  # Discord requires defer for long operations

    try:
        # Call the agent endpoint
        result = await api_client.query_knowledge_store(query)

        # Extract response from agent
        response_text = result.get("response", "No response received")

        # Discord has a 2000 character limit per message
        # Split into chunks if needed
        if len(response_text) <= 2000:
            await interaction.followup.send(response_text)
        else:
            # Split into multiple messages
            chunks = [response_text[i : i + 2000] for i in range(0, len(response_text), 2000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await interaction.followup.send(chunk)
                else:
                    await interaction.followup.send(chunk)

    except Exception as e:
        logger.exception(f"Error querying knowledge store: {e}")
        await interaction.followup.send(f"Error querying knowledge store: {str(e)}", ephemeral=True)
