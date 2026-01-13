"""Integration tests for UploadCapability workflow."""

from unittest.mock import AsyncMock, patch

import pytest
from bot.capabilities.upload import UploadCapability
from bot.immich_client import ImmichClient


@pytest.fixture
def upload_capability_with_real_client(mock_discord_client):
    """Create UploadCapability with real ImmichClient (to be mocked in tests)."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    return UploadCapability(client=mock_discord_client, immich_client=immich_client)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_upload_flow(
    test_database, mock_discord_message, mock_discord_attachment, mock_discord_client
):
    """Test complete upload flow from message to Immich via capability."""
    # Setup: Message in upload channel with valid attachment
    mock_discord_message.channel.id = 987654321  # Upload channel
    mock_discord_message.attachments = [mock_discord_attachment]
    mock_discord_message.author.display_name = "TestUser"

    # Create capability with real Immich client (will be mocked)
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(client=mock_discord_client, immich_client=immich_client)

    # Mock Immich upload
    with patch.object(immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123", "type": "IMAGE"}

        # Execute capability message handler
        result = await capability.on_message(mock_discord_message)

        # Verify upload was called with correct parameters
        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["filename"] == "test.jpg"
        assert "TestUser" in call_kwargs["description"]
        assert call_kwargs["file_data"] == b"fake_image_data"

        # Verify Discord responses
        mock_discord_message.add_reaction.assert_called_once_with("✅")
        mock_discord_message.reply.assert_called_once()
        reply_text = mock_discord_message.reply.call_args[0][0]
        assert "successfully uploaded" in reply_text.lower()
        assert "asset123" in reply_text

        # on_message returns False to allow other capabilities to also process
        assert result is False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_flow_error_handling(
    test_database, mock_discord_message, mock_discord_attachment, mock_discord_client
):
    """Test upload flow handles errors correctly via capability."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.attachments = [mock_discord_attachment]

    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(client=mock_discord_client, immich_client=immich_client)

    # Mock Immich upload failure
    with patch.object(immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.side_effect = Exception("Immich API error: 500")

        # Execute capability message handler
        await capability.on_message(mock_discord_message)

        # Verify error handling
        mock_discord_message.add_reaction.assert_called_once_with("❌")
        mock_discord_message.reply.assert_called_once()
        reply_text = mock_discord_message.reply.call_args[0][0]
        assert "failed" in reply_text.lower() or "error" in reply_text.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_flow_multiple_files(test_database, mock_discord_message, mock_discord_client):
    """Test upload flow with multiple attachments via capability."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.author.display_name = "TestUser"

    # Create multiple attachments
    attachment1 = AsyncMock()
    attachment1.filename = "test1.jpg"
    attachment1.size = 1024 * 1024
    attachment1.read = AsyncMock(return_value=b"image1_data")

    attachment2 = AsyncMock()
    attachment2.filename = "test2.png"
    attachment2.size = 512 * 1024
    attachment2.read = AsyncMock(return_value=b"image2_data")

    mock_discord_message.attachments = [attachment1, attachment2]

    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(client=mock_discord_client, immich_client=immich_client)

    with patch.object(immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        await capability.on_message(mock_discord_message)

        # Both files should be uploaded
        assert mock_upload.call_count == 2

        # Verify both files processed
        filenames = [call[1]["filename"] for call in mock_upload.call_args_list]
        assert "test1.jpg" in filenames
        assert "test2.png" in filenames


@pytest.mark.asyncio
@pytest.mark.integration
async def test_capability_integration_with_registry(
    mock_discord_client, mock_discord_message, mock_discord_attachment
):
    """Test UploadCapability works correctly when registered via CapabilityRegistry."""
    from bot.capabilities.registry import CapabilityRegistry
    from bot.immich_client import ImmichClient

    # Setup
    mock_discord_message.channel.id = 987654321
    mock_discord_message.attachments = [mock_discord_attachment]

    # Create registry and register capability
    registry = CapabilityRegistry(client=mock_discord_client)
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(client=mock_discord_client, immich_client=immich_client)
    registry.register(capability)

    # Mock Immich upload
    with patch.object(immich_client, "upload_asset", new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}

        # Process message through registry
        await registry.handle_message(mock_discord_message)

        # Verify upload was processed
        mock_upload.assert_called_once()
