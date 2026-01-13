"""Upload capability - handles file uploads to Immich and face claiming."""

import logging

import aiohttp
import discord
from discord import Interaction, app_commands
from discord.ui import Select, View

from bot.capabilities.base import BaseCapability
from bot.config import config
from bot.database import Database
from bot.immich_client import ImmichClient
from bot.utils import format_file_size, is_valid_media_file

logger = logging.getLogger(__name__)

# Discord file size limit is 25MB
DISCORD_FILE_SIZE_LIMIT = 25 * 1024 * 1024  # 25MB in bytes


class PersonSelectView(View):
    """View for selecting a person from search results."""

    def __init__(
        self,
        people: list[dict],
        immich_client: ImmichClient,
        database: Database,
        user_id: str,
    ):
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


class UploadCapability(BaseCapability):
    """
    Upload capability that handles file uploads to Immich and face claiming.

    When enabled, the bot will:
    - Automatically upload media files from Discord messages to Immich
    - Provide /claim_face command to link Discord users to Immich person profiles
    """

    name = "upload"
    description = "Uploads media files to Immich photo library and manages face claiming"
    priority = 100  # Lower priority than echo (runs after echo)

    def __init__(
        self,
        client: discord.Client,
        immich_client: ImmichClient,
        database: Database | None = None,
        settings: dict | None = None,
    ):
        """
        Initialize the upload capability.

        Args:
            client: The Discord client instance
            immich_client: The Immich client for uploading files
            database: The database for user mappings (optional, creates new if not provided)
            settings: Optional capability-specific settings from Lambda API
        """
        super().__init__(client, settings=settings)
        self.immich_client = immich_client
        self.database = database

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when bot is ready. Registers the /claim_face command.

        Args:
            tree: The command tree to register commands with
        """
        # Register /claim_face command
        await self._register_claim_face_command(tree)

        logger.info(
            f"Upload capability ready - monitoring "
            f"{'channel ' + config.DISCORD_UPLOAD_CHANNEL_ID if config.DISCORD_UPLOAD_CHANNEL_ID else 'all channels'}"
        )

    async def _register_claim_face_command(self, tree: app_commands.CommandTree) -> None:
        """Register the /claim_face slash command."""
        if self.database is None:
            logger.warning(
                "Database not provided to UploadCapability - /claim_face command disabled"
            )
            return

        @tree.command(
            name="claim_face",
            description="Link your Discord account to your Immich person profile",
        )
        @app_commands.describe(search_name="Name to search for in Immich")
        async def claim_face(interaction: Interaction, search_name: str):
            """Handle /claim_face command."""
            await interaction.response.defer(ephemeral=True)

            try:
                # Search for people
                people = await self.immich_client.search_people(search_name)

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
                    await self.database.save_user_mapping(
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
                        immich_client=self.immich_client,
                        database=self.database,
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

    async def on_message(self, message: discord.Message) -> bool:
        """
        Handle incoming messages with file attachments.

        Args:
            message: The Discord message

        Returns:
            True if files were uploaded, False otherwise
        """
        # Check if message has attachments
        if not message.attachments:
            return False

        # If DISCORD_UPLOAD_CHANNEL_ID is set, only allow uploads from that channel
        if (
            config.DISCORD_UPLOAD_CHANNEL_ID
            and str(message.channel.id) != config.DISCORD_UPLOAD_CHANNEL_ID
        ):
            return False

        # Process uploads
        await self._handle_uploads(message)

        # Return False to allow other capabilities to also process the message
        # (e.g., if someone @mentions the bot with an attachment)
        return False

    async def _handle_uploads(self, message: discord.Message) -> bool:
        """
        Handle file uploads from Discord message.

        Args:
            message: The Discord message with attachments

        Returns:
            True if any files were uploaded successfully
        """
        uploaded_any = False

        for attachment in message.attachments:
            # Validate file type
            if not is_valid_media_file(attachment.filename):
                continue

            # Check file size
            if attachment.size > DISCORD_FILE_SIZE_LIMIT:
                await message.reply(
                    f"❌ File `{attachment.filename}` is too large ({format_file_size(attachment.size)}). "
                    f"Discord limit is {format_file_size(DISCORD_FILE_SIZE_LIMIT)}. "
                    "Please use a direct upload link instead."
                )
                continue

            try:
                # Download file
                file_data = await attachment.read()
                filename = attachment.filename

                # Try to get user-specific Immich API key
                user_api_key = await self._get_user_immich_api_key(str(message.author.id))

                # Use user-specific API key if available, otherwise use global client
                if user_api_key:
                    # Create a new client with user-specific API key
                    upload_client = ImmichClient(api_key=user_api_key)
                else:
                    # Fallback to global client (or use default from config)
                    upload_client = self.immich_client

                # Upload to Immich
                description = f"Uploaded by {message.author.display_name}"
                result = await upload_client.upload_asset(
                    file_data=file_data, filename=filename, description=description
                )

                # Reply with success
                await message.add_reaction("✅")
                await message.reply(
                    f"✅ Successfully uploaded `{filename}` to Immich!\n"
                    f"Asset ID: `{result.get('id', 'N/A')}`"
                )
                uploaded_any = True

            except Exception as e:
                # Log error and notify user
                logger.exception(f"Failed to upload {attachment.filename}")
                error_msg = str(e)
                await message.add_reaction("❌")
                await message.reply(
                    f"❌ Failed to upload `{attachment.filename}` to Immich: {error_msg}"
                )

        return uploaded_any

    async def _get_user_immich_api_key(self, discord_user_id: str) -> str | None:
        """
        Get user's Immich API key from Lambda API.

        Args:
            discord_user_id: Discord user ID

        Returns:
            Immich API key or None if not found/error
        """
        if not config.CLOUDFLARE_EMAIL:
            logger.debug("CLOUDFLARE_EMAIL not configured, using global API key")
            return None

        try:
            # First, get user by Discord ID to find their email
            # Note: This requires the user to have linked their Discord account via /api/me/discord/link
            # For now, we'll use a fallback to the global API key if user-specific lookup fails
            async with aiohttp.ClientSession() as session:
                # Try to get API key directly (Lambda API will handle user lookup)
                # Since we don't have Cloudflare JWT in Discord bot, we'll need to use a service key
                # or implement a different approach
                # For now, return None to use fallback
                return None
        except Exception as e:
            logger.warning(f"Failed to get user Immich API key: {e}")
            return None
