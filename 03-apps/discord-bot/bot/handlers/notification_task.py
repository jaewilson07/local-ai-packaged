"""Background task for checking new assets and sending notifications."""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

import discord

from bot.config import config
from bot.database import Database
from bot.immich_client import ImmichClient
from bot.utils import get_immich_gallery_url

logger = logging.getLogger(__name__)


class NotificationTask:
    """Background task that polls Immich for new assets and sends notifications."""

    def __init__(
        self,
        client: discord.Client,
        immich_client: ImmichClient,
        database: Database,
    ):
        self.client = client
        self.immich_client = immich_client
        self.database = database
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the notification polling task."""
        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("Notification task started")

    async def stop(self) -> None:
        """Stop the notification polling task."""
        self.running = False
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        logger.info("Notification task stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        # Initialize last check timestamp if not exists
        last_check = await self.database.get_last_check_timestamp()
        if not last_check:
            # Start checking from 1 hour ago to catch recent uploads
            last_check = datetime.utcnow() - timedelta(hours=1)
            await self.database.update_last_check_timestamp(last_check)

        while self.running:
            try:
                # Check for new assets
                new_assets = await self.immich_client.list_new_assets(last_check)

                for asset in new_assets:
                    await self._process_asset(asset)

                # Update last check timestamp
                new_check = datetime.utcnow()
                await self.database.update_last_check_timestamp(new_check)
                last_check = new_check

            except Exception as e:
                logger.exception(f"Error in notification polling: {e}")

            # Wait before next check
            await asyncio.sleep(config.NOTIFICATION_POLL_INTERVAL)

    async def _process_asset(self, asset: dict) -> None:
        """Process a single asset and send notifications if needed."""
        asset_id = asset.get("id")
        if not asset_id:
            return

        try:
            # Get faces for this asset
            faces = await self.immich_client.get_asset_faces(asset_id)

            if not faces:
                return  # No faces detected

            # Process each face
            notified_users = set()  # Avoid duplicate notifications
            for face in faces:
                person_id = face.get("personId")
                if not person_id:
                    continue

                # Check if we have a Discord user mapped to this person
                user = await self.database.get_user_by_immich_person_id(person_id)
                if not user:
                    continue

                discord_id = user.get("discord_id")
                if not discord_id or discord_id in notified_users:
                    continue

                # Send DM notification
                await self._send_notification(discord_id, asset)
                notified_users.add(discord_id)

        except Exception as e:
            logger.exception(f"Error processing asset {asset_id}: {e}")

    async def _send_notification(self, discord_id: str, asset: dict) -> None:
        """Send DM notification to Discord user."""
        try:
            user = await self.client.fetch_user(int(discord_id))
            if not user:
                logger.warning(f"Could not fetch Discord user {discord_id}")
                return

            asset_id = asset.get("id")
            asset_type = asset.get("type", "photo")
            thumbnail_url = await self.immich_client.get_asset_thumbnail(asset_id)
            gallery_url = get_immich_gallery_url(asset_id, self.immich_client.base_url)

            # Create embed
            embed = discord.Embed(
                title="📸 You were spotted in a new photo!",
                description=f"A new {asset_type} with your face has been uploaded to Immich.",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Asset ID", value=asset_id, inline=False)
            if thumbnail_url:
                embed.set_image(url=thumbnail_url)
            embed.add_field(
                name="View in Gallery",
                value=f"[Open in Immich]({gallery_url})",
                inline=False,
            )

            await user.send(embed=embed)
            logger.info(f"Sent notification to Discord user {discord_id} for asset {asset_id}")

        except discord.Forbidden:
            logger.warning(f"Could not send DM to user {discord_id} (DMs disabled or blocked)")
        except Exception as e:
            logger.exception(f"Error sending notification to {discord_id}: {e}")
