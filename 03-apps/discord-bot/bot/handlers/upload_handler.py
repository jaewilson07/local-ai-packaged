"""Handler for file uploads to Discord."""

from discord import Message

from bot.config import config
from bot.immich_client import ImmichClient
from bot.utils import format_file_size, is_valid_media_file

# Discord file size limit is 25MB
DISCORD_FILE_SIZE_LIMIT = 25 * 1024 * 1024  # 25MB in bytes


async def handle_upload(message: Message, immich_client: ImmichClient) -> None:
    """Handle file upload in #event-uploads channel."""
    # Check if message is in the upload channel
    if str(message.channel.id) != config.DISCORD_UPLOAD_CHANNEL_ID:
        return

    # Check if message has attachments
    if not message.attachments:
        return

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

            # Upload to Immich
            description = f"Uploaded by {message.author.display_name}"
            result = await immich_client.upload_asset(
                file_data=file_data, filename=filename, description=description
            )

            # Reply with success
            await message.add_reaction("✅")
            await message.reply(
                f"✅ Successfully uploaded `{filename}` to Immich!\n"
                f"Asset ID: `{result.get('id', 'N/A')}`"
            )

        except Exception as e:
            # Log error and notify user
            error_msg = str(e)
            await message.add_reaction("❌")
            await message.reply(
                f"❌ Failed to upload `{attachment.filename}` to Immich: {error_msg}"
            )
