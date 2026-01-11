"""Integration tests for upload workflow."""

import pytest
from unittest.mock import AsyncMock, patch
from bot.handlers.upload_handler import handle_upload
from bot.immich_client import ImmichClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_upload_flow(
    test_database, mock_discord_message, mock_discord_attachment
):
    """Test complete upload flow from message to Immich."""
    # Setup: Message in upload channel with valid attachment
    mock_discord_message.channel.id = 987654321  # Upload channel
    mock_discord_message.attachments = [mock_discord_attachment]
    mock_discord_message.author.display_name = "TestUser"
    
    # Create real Immich client (will be mocked)
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    # Mock Immich upload
    with patch.object(immich_client, 'upload_asset', new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123", "type": "IMAGE"}
        
        # Execute upload handler
        await handle_upload(mock_discord_message, immich_client)
        
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_flow_error_handling(
    test_database, mock_discord_message, mock_discord_attachment
):
    """Test upload flow handles errors correctly."""
    mock_discord_message.channel.id = 987654321
    mock_discord_message.attachments = [mock_discord_attachment]
    
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    # Mock Immich upload failure
    with patch.object(immich_client, 'upload_asset', new_callable=AsyncMock) as mock_upload:
        mock_upload.side_effect = Exception("Immich API error: 500")
        
        # Execute upload handler
        await handle_upload(mock_discord_message, immich_client)
        
        # Verify error handling
        mock_discord_message.add_reaction.assert_called_once_with("❌")
        mock_discord_message.reply.assert_called_once()
        reply_text = mock_discord_message.reply.call_args[0][0]
        assert "failed" in reply_text.lower() or "error" in reply_text.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_flow_multiple_files(
    test_database, mock_discord_message
):
    """Test upload flow with multiple attachments."""
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
    
    with patch.object(immich_client, 'upload_asset', new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = {"id": "asset123"}
        
        await handle_upload(mock_discord_message, immich_client)
        
        # Both files should be uploaded
        assert mock_upload.call_count == 2
        
        # Verify both files processed
        filenames = [call[1]["filename"] for call in mock_upload.call_args_list]
        assert "test1.jpg" in filenames
        assert "test2.png" in filenames
