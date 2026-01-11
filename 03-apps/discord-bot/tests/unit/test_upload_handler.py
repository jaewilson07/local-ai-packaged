"""Tests for upload handler."""

from unittest.mock import AsyncMock, patch

import pytest
from bot.handlers.upload_handler import DISCORD_FILE_SIZE_LIMIT, handle_upload


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_success(
    mock_discord_message, mock_discord_attachment, mock_immich_client
):
    """Test successful file upload."""
    # Setup message in upload channel
    mock_discord_message.channel.id = 987654321  # Upload channel ID
    mock_discord_message.attachments = [mock_discord_attachment]

    # Mock Immich upload response
    with patch.object(mock_immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123", "type": "IMAGE"}

        await handle_upload(mock_discord_message, mock_immich_client)

        # Verify upload was called
        mock_upload.assert_called_once()
        assert mock_upload.call_args[1]["filename"] == "test.jpg"

        # Verify reactions and replies
        mock_discord_message.add_reaction.assert_called_once_with("✅")
        mock_discord_message.reply.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_wrong_channel(mock_discord_message, mock_immich_client):
    """Test upload handler ignores messages in wrong channel."""
    # Set message to different channel
    mock_discord_message.channel.id = 111222333  # Not upload channel
    mock_discord_message.attachments = []

    await handle_upload(mock_discord_message, mock_immich_client)

    # Should not process
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_no_attachments(mock_discord_message, mock_immich_client):
    """Test upload handler ignores messages without attachments."""
    mock_discord_message.channel.id = 987654321  # Upload channel
    mock_discord_message.attachments = []

    await handle_upload(mock_discord_message, mock_immich_client)

    # Should not process
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_invalid_file_type(mock_discord_message, mock_immich_client):
    """Test upload handler ignores invalid file types."""
    mock_discord_message.channel.id = 987654321
    invalid_attachment = AsyncMock()
    invalid_attachment.filename = "document.pdf"
    invalid_attachment.size = 1024
    mock_discord_message.attachments = [invalid_attachment]

    await handle_upload(mock_discord_message, mock_immich_client)

    # Should not process invalid file types
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_file_too_large(
    mock_discord_message, mock_discord_attachment, mock_immich_client
):
    """Test upload handler rejects files larger than Discord limit."""
    mock_discord_message.channel.id = 987654321
    mock_discord_attachment.size = DISCORD_FILE_SIZE_LIMIT + 1  # Too large
    mock_discord_message.attachments = [mock_discord_attachment]

    await handle_upload(mock_discord_message, mock_immich_client)

    # Should reply with error
    mock_discord_message.reply.assert_called_once()
    reply_call = mock_discord_message.reply.call_args[0][0]
    assert "too large" in reply_call.lower()
    assert "25MB" in reply_call or "discord limit" in reply_call.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_multiple_attachments(mock_discord_message, mock_immich_client):
    """Test upload handler processes multiple attachments."""
    mock_discord_message.channel.id = 987654321

    # Create multiple valid attachments
    attachment1 = AsyncMock()
    attachment1.filename = "test1.jpg"
    attachment1.size = 1024 * 1024
    attachment1.read = AsyncMock(return_value=b"image1")

    attachment2 = AsyncMock()
    attachment2.filename = "test2.png"
    attachment2.size = 512 * 1024
    attachment2.read = AsyncMock(return_value=b"image2")

    mock_discord_message.attachments = [attachment1, attachment2]

    with patch.object(mock_immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await handle_upload(mock_discord_message, mock_immich_client)

        # Should process both attachments
        assert mock_upload.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_immich_error(
    mock_discord_message, mock_discord_attachment, mock_immich_client
):
    """Test upload handler handles Immich API errors."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.attachments = [mock_discord_attachment]

    with patch.object(mock_immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.side_effect = Exception("Immich API error")

        await handle_upload(mock_discord_message, mock_immich_client)

        # Should reply with error
        mock_discord_message.add_reaction.assert_called_once_with("❌")
        mock_discord_message.reply.assert_called_once()
        reply_call = mock_discord_message.reply.call_args[0][0]
        assert "failed" in reply_call.lower() or "error" in reply_call.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_mixed_attachments(mock_discord_message, mock_immich_client):
    """Test upload handler handles mix of valid and invalid attachments."""
    mock_discord_message.channel.id = 987654321

    valid_attachment = AsyncMock()
    valid_attachment.filename = "test.jpg"
    valid_attachment.size = 1024 * 1024
    valid_attachment.read = AsyncMock(return_value=b"image")

    invalid_attachment = AsyncMock()
    invalid_attachment.filename = "document.pdf"
    invalid_attachment.size = 1024

    too_large_attachment = AsyncMock()
    too_large_attachment.filename = "huge.mp4"
    too_large_attachment.size = DISCORD_FILE_SIZE_LIMIT + 1

    mock_discord_message.attachments = [
        valid_attachment,
        invalid_attachment,
        too_large_attachment,
    ]

    with patch.object(mock_immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await handle_upload(mock_discord_message, mock_immich_client)

        # Should only process valid attachment
        mock_upload.assert_called_once()
        # Should reply for too large file
        assert mock_discord_message.reply.call_count >= 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_upload_sets_description(
    mock_discord_message, mock_discord_attachment, mock_immich_client
):
    """Test upload handler sets correct description with author name."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.author.display_name = "TestUser"
    mock_discord_message.attachments = [mock_discord_attachment]

    with patch.object(mock_immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await handle_upload(mock_discord_message, mock_immich_client)

        # Verify description includes author name
        call_kwargs = mock_upload.call_args[1]
        assert "description" in call_kwargs
        assert "TestUser" in call_kwargs["description"]
