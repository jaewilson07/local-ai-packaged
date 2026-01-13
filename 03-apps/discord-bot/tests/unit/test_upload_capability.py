"""Tests for UploadCapability."""

from unittest.mock import AsyncMock, patch

import pytest
from bot.capabilities.upload import DISCORD_FILE_SIZE_LIMIT, UploadCapability


@pytest.fixture
def upload_capability(mock_discord_client, mock_immich_client):
    """Create UploadCapability instance for testing."""
    return UploadCapability(client=mock_discord_client, immich_client=mock_immich_client)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_success(
    upload_capability, mock_discord_message, mock_discord_attachment
):
    """Test successful file upload via capability."""
    # Setup message in upload channel
    mock_discord_message.channel.id = 987654321  # Upload channel ID
    mock_discord_message.attachments = [mock_discord_attachment]

    # Mock Immich upload response
    with patch.object(
        upload_capability.immich_client, "upload_asset", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.return_value = {"id": "asset123", "type": "IMAGE"}

        result = await upload_capability.on_message(mock_discord_message)

        # Verify upload was called
        mock_upload.assert_called_once()
        assert mock_upload.call_args[1]["filename"] == "test.jpg"

        # Verify reactions and replies
        mock_discord_message.add_reaction.assert_called_once_with("✅")
        mock_discord_message.reply.assert_called_once()

        # on_message returns False to allow other capabilities to process
        assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_wrong_channel(
    upload_capability, mock_discord_message, mock_discord_attachment
):
    """Test upload capability ignores messages in wrong channel."""
    # Set message to different channel
    mock_discord_message.channel.id = 111222333  # Not upload channel
    mock_discord_message.attachments = [mock_discord_attachment]

    result = await upload_capability.on_message(mock_discord_message)

    # Should not process
    assert result is False
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_no_attachments(upload_capability, mock_discord_message):
    """Test upload capability ignores messages without attachments."""
    mock_discord_message.channel.id = 987654321  # Upload channel
    mock_discord_message.attachments = []

    result = await upload_capability.on_message(mock_discord_message)

    # Should not process
    assert result is False
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_invalid_file_type(upload_capability, mock_discord_message):
    """Test upload capability ignores invalid file types."""
    mock_discord_message.channel.id = 987654321
    invalid_attachment = AsyncMock()
    invalid_attachment.filename = "document.pdf"
    invalid_attachment.size = 1024
    mock_discord_message.attachments = [invalid_attachment]

    result = await upload_capability.on_message(mock_discord_message)

    # Should not process invalid file types
    assert result is False
    mock_discord_message.reply.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_file_too_large(
    upload_capability, mock_discord_message, mock_discord_attachment
):
    """Test upload capability rejects files larger than Discord limit."""
    mock_discord_message.channel.id = 987654321
    mock_discord_attachment.size = DISCORD_FILE_SIZE_LIMIT + 1  # Too large
    mock_discord_message.attachments = [mock_discord_attachment]

    result = await upload_capability.on_message(mock_discord_message)

    # Should reply with error
    mock_discord_message.reply.assert_called_once()
    reply_call = mock_discord_message.reply.call_args[0][0]
    assert "too large" in reply_call.lower()
    assert "25MB" in reply_call or "discord limit" in reply_call.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_multiple_attachments(upload_capability, mock_discord_message):
    """Test upload capability processes multiple attachments."""
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

    with patch.object(
        upload_capability.immich_client, "upload_asset", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await upload_capability.on_message(mock_discord_message)

        # Should process both attachments
        assert mock_upload.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_immich_error(
    upload_capability, mock_discord_message, mock_discord_attachment
):
    """Test upload capability handles Immich API errors."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.attachments = [mock_discord_attachment]

    with patch.object(
        upload_capability.immich_client, "upload_asset", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.side_effect = Exception("Immich API error")

        await upload_capability.on_message(mock_discord_message)

        # Should reply with error
        mock_discord_message.add_reaction.assert_called_once_with("❌")
        mock_discord_message.reply.assert_called_once()
        reply_call = mock_discord_message.reply.call_args[0][0]
        assert "failed" in reply_call.lower() or "error" in reply_call.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_mixed_attachments(upload_capability, mock_discord_message):
    """Test upload capability handles mix of valid and invalid attachments."""
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

    with patch.object(
        upload_capability.immich_client, "upload_asset", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await upload_capability.on_message(mock_discord_message)

        # Should only process valid attachment
        mock_upload.assert_called_once()
        # Should reply for too large file
        assert mock_discord_message.reply.call_count >= 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_sets_description(
    upload_capability, mock_discord_message, mock_discord_attachment
):
    """Test upload capability sets correct description with author name."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.author.display_name = "TestUser"
    mock_discord_message.attachments = [mock_discord_attachment]

    with patch.object(
        upload_capability.immich_client, "upload_asset", new_callable=AsyncMock
    ) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await upload_capability.on_message(mock_discord_message)

        # Verify description includes author name
        call_kwargs = mock_upload.call_args[1]
        assert "description" in call_kwargs
        assert "TestUser" in call_kwargs["description"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_name_and_description(upload_capability):
    """Test capability metadata."""
    assert upload_capability.name == "upload"
    assert "Immich" in upload_capability.description


@pytest.mark.asyncio
@pytest.mark.unit
async def test_upload_capability_priority(upload_capability):
    """Test capability priority is set correctly."""
    # Priority 100 means it runs after higher-priority capabilities
    assert upload_capability.priority == 100
