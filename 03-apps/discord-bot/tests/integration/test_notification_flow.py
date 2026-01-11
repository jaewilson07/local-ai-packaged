"""Integration tests for notification workflow."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from bot.handlers.notification_task import NotificationTask


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_notification_flow(
    test_database, mock_discord_client, sample_immich_asset, sample_immich_faces
):
    """Test complete notification flow from new asset to DM."""
    # Setup: Create user mapping
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )
    
    # Create Immich client (will be mocked)
    from bot.immich_client import ImmichClient
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    # Create notification task
    notification_task = NotificationTask(
        client=mock_discord_client,
        immich_client=immich_client,
        database=test_database,
    )
    
    # Mock Immich API calls
    with patch.object(immich_client, 'get_asset_faces', new_callable=AsyncMock) as mock_faces:
        mock_faces.return_value = sample_immich_faces
        
        with patch.object(immich_client, 'get_asset_thumbnail', new_callable=AsyncMock) as mock_thumb:
            mock_thumb.return_value = "http://test/thumb.jpg"
            
            # Mock Discord user fetch and send
            mock_user = AsyncMock()
            mock_user.send = AsyncMock()
            mock_discord_client.fetch_user = AsyncMock(return_value=mock_user)
            
            # Process asset
            await notification_task._process_asset(sample_immich_asset)
            
            # Verify faces were fetched
            mock_faces.assert_called_once_with(sample_immich_asset["id"])
            
            # Verify notification was sent
            mock_user.send.assert_called_once()
            call_kwargs = mock_user.send.call_args[1]
            assert "embed" in call_kwargs
            
            embed = call_kwargs["embed"]
            assert "spotted" in embed.title.lower()
            assert sample_immich_asset["id"] in str(embed.fields)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_notification_flow_no_faces(
    test_database, mock_discord_client, sample_immich_asset
):
    """Test notification flow when asset has no faces."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )
    
    from bot.immich_client import ImmichClient
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    notification_task = NotificationTask(
        client=mock_discord_client,
        immich_client=immich_client,
        database=test_database,
    )
    
    with patch.object(immich_client, 'get_asset_faces', new_callable=AsyncMock) as mock_faces:
        mock_faces.return_value = []  # No faces
        
        await notification_task._process_asset(sample_immich_asset)
        
        # Should not send notification
        mock_discord_client.fetch_user.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_notification_flow_timestamp_tracking(
    test_database, mock_discord_client
):
    """Test notification flow updates timestamp correctly."""
    from bot.immich_client import ImmichClient
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    notification_task = NotificationTask(
        client=mock_discord_client,
        immich_client=immich_client,
        database=test_database,
    )
    
    # Set initial timestamp
    initial_time = datetime.utcnow() - timedelta(hours=1)
    await test_database.update_last_check_timestamp(initial_time)
    
    with patch.object(immich_client, 'list_new_assets', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        
        # Start task briefly
        await notification_task.start()
        await asyncio.sleep(0.1)
        await notification_task.stop()
        
        # Verify timestamp was updated
        updated_timestamp = await test_database.get_last_check_timestamp()
        assert updated_timestamp > initial_time
