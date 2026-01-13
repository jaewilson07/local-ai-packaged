"""
DEPRECATED: Legacy command handler.

This module is deprecated. Command handling has been migrated to capabilities:
    - /claim_face -> bot.capabilities.upload.UploadCapability

This file is kept for backward compatibility with existing tests only.
"""

import warnings

import discord
from discord import Interaction, app_commands
from discord.ui import Select, View

from bot.database import Database
from bot.immich_client import ImmichClient

# Emit deprecation warning when module is imported
warnings.warn(
    "bot.handlers.command_handler is deprecated. "
    "Use bot.capabilities.upload.UploadCapability instead for /claim_face command.",
    DeprecationWarning,
    stacklevel=2,
)


class PersonSelectView(View):
    """
    DEPRECATED: View for selecting a person from search results.

    This class is deprecated. Use bot.capabilities.upload.PersonSelectView instead.
    """

    def __init__(
        self,
        people: list[dict],
        immich_client: ImmichClient,
        database: Database,
        user_id: str,
    ):
        warnings.warn(
            "PersonSelectView is deprecated. Use bot.capabilities.upload.PersonSelectView instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(timeout=60.0)
        self.people = people
        self.immich_client = immich_client
        self.database = database
        self.user_id = user_id

        # Create select menu
        select_options = []
        for person in people[:25]:  # Discord limit is 25 options
            name = person.get("name", "Unknown")
            person_id = person.get("id", "")
            select_options.append(
                discord.SelectOption(
                    label=name[:100],  # Discord limit is 100 chars
                    value=person_id,
                    description=f"Person ID: {person_id[:50]}",
                )
            )

        self.select_menu = Select(
            placeholder="Select the person that matches you...",
            min_values=1,
            max_values=1,
            options=select_options,
        )
        self.select_menu.callback = self._on_select
        self.add_item(self.select_menu)

    async def _on_select(self, interaction: Interaction):
        """Handle person selection."""
        if not self.select_menu.values:
            await interaction.response.send_message("❌ No selection made.", ephemeral=True)
            return

        selected_id = self.select_menu.values[0]
        person = next((p for p in self.people if p.get("id") == selected_id), None)

        if not person:
            await interaction.response.send_message("❌ Invalid selection.", ephemeral=True)
            return

        # Save mapping
        await self.database.save_user_mapping(
            discord_id=self.user_id, immich_person_id=person["id"], notify_enabled=True
        )

        await interaction.response.send_message(
            f"✅ Successfully mapped your Discord account to **{person.get('name', 'Unknown')}** in Immich!\n"
            "You will now receive notifications when you're detected in new photos.",
            ephemeral=True,
        )
        self.stop()

    async def on_timeout(self):
        """Handle view timeout."""
        self.stop()


async def setup_claim_face_command(
    tree: app_commands.CommandTree, immich_client: ImmichClient, database: Database
) -> None:
    """
    DEPRECATED: Register the /claim_face command.

    This function is deprecated. The /claim_face command is now registered by
    UploadCapability.on_ready().

    This function is kept for backward compatibility with existing tests only.
    """
    warnings.warn(
        "setup_claim_face_command() is deprecated. Use UploadCapability.on_ready() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    @tree.command(
        name="claim_face", description="Link your Discord account to your Immich person profile"
    )
    @app_commands.describe(search_name="Name to search for in Immich")
    async def claim_face(interaction: Interaction, search_name: str):
        """Handle /claim_face command."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Search for people
            people = await immich_client.search_people(search_name)

            if not people:
                await interaction.followup.send(
                    f"❌ No people found matching '{search_name}' in Immich.\n"
                    "Make sure the person exists in Immich and try a different search term.",
                    ephemeral=True,
                )
                return

            # Send response with select menu
            if len(people) == 1:
                # Auto-select if only one result
                person = people[0]
                await database.save_user_mapping(
                    discord_id=str(interaction.user.id),
                    immich_person_id=person["id"],
                    notify_enabled=True,
                )
                await interaction.followup.send(
                    f"✅ Found one match: **{person.get('name', 'Unknown')}**\n"
                    "Your Discord account has been linked! You will receive notifications when you're detected in new photos.",
                    ephemeral=True,
                )
            else:
                # Create view with select menu
                view = PersonSelectView(
                    people=people,
                    immich_client=immich_client,
                    database=database,
                    user_id=str(interaction.user.id),
                )
                await interaction.followup.send(
                    f"Found {len(people)} people matching '{search_name}'. Please select the one that matches you:",
                    view=view,
                    ephemeral=True,
                )

        except Exception as e:
            error_msg = str(e)
            await interaction.followup.send(
                f"❌ Error searching for people: {error_msg}", ephemeral=True
            )
