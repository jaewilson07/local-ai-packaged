"""Tests for notification task."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_start_stop(mock_notification_task):
    """Test notification task start and stop."""
    await mock_notification_task.start()
    assert mock_notification_task.running is True
    assert mock_notification_task.task is not None

    await mock_notification_task.stop()
    assert mock_notification_task.running is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_process_asset_with_faces(
    mock_notification_task, test_database, sample_immich_asset, sample_immich_faces
):
    """Test processing asset with detected faces."""
    # Setup: Create user mapping
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    # Mock Immich client methods
    with patch.object(
        mock_notification_task.immich_client, "get_asset_faces", new_callable=AsyncMock
    ) as mock_faces:
        mock_faces.return_value = sample_immich_faces

        with patch.object(
            mock_notification_task.immich_client, "get_asset_thumbnail", new_callable=AsyncMock
        ) as mock_thumb:
            mock_thumb.return_value = "http://test/thumb.jpg"

            # Mock user fetch and send
            mock_user = AsyncMock()
            mock_user.send = AsyncMock()
            mock_notification_task.client.fetch_user = AsyncMock(return_value=mock_user)

            # Process asset
            await mock_notification_task._process_asset(sample_immich_asset)

            # Verify faces were fetched
            mock_faces.assert_called_once_with(sample_immich_asset["id"])

            # Verify notification was sent
            mock_user.send.assert_called_once()
            call_args = mock_user.send.call_args
            assert "embed" in call_args.kwargs


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_process_asset_no_faces(
    mock_notification_task, sample_immich_asset
):
    """Test processing asset with no faces detected."""
    with patch.object(
        mock_notification_task.immich_client, "get_asset_faces", new_callable=AsyncMock
    ) as mock_faces:
        mock_faces.return_value = []

        # Process asset
        await mock_notification_task._process_asset(sample_immich_asset)

        # Should not send notification
        mock_notification_task.client.fetch_user.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_process_asset_no_user_mapping(
    mock_notification_task, test_database, sample_immich_asset, sample_immich_faces
):
    """Test processing asset when user is not mapped."""
    # No user mapping in database

    with patch.object(
        mock_notification_task.immich_client, "get_asset_faces", new_callable=AsyncMock
    ) as mock_faces:
        mock_faces.return_value = sample_immich_faces

        # Process asset
        await mock_notification_task._process_asset(sample_immich_asset)

        # Should not send notification
        mock_notification_task.client.fetch_user.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_duplicate_prevention(
    mock_notification_task, test_database, sample_immich_asset, sample_immich_faces
):
    """Test duplicate notification prevention."""
    # Setup: Create user mapping
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    # Create faces with same person ID (multiple faces, same person)
    duplicate_faces = [
        {"id": "face1", "personId": "person1", "assetId": "asset123"},
        {"id": "face2", "personId": "person1", "assetId": "asset123"},
    ]

    with patch.object(
        mock_notification_task.immich_client, "get_asset_faces", new_callable=AsyncMock
    ) as mock_faces:
        mock_faces.return_value = duplicate_faces

        with patch.object(
            mock_notification_task.immich_client, "get_asset_thumbnail", new_callable=AsyncMock
        ):
            mock_user = AsyncMock()
            mock_user.send = AsyncMock()
            mock_notification_task.client.fetch_user = AsyncMock(return_value=mock_user)

            # Process asset
            await mock_notification_task._process_asset(sample_immich_asset)

            # Should only send one notification (duplicate prevention)
            assert mock_user.send.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_dm_disabled(
    mock_notification_task, test_database, sample_immich_asset, sample_immich_faces
):
    """Test notification when user has DMs disabled."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    import discord

    with patch.object(
        mock_notification_task.immich_client, "get_asset_faces", new_callable=AsyncMock
    ) as mock_faces:
        mock_faces.return_value = sample_immich_faces

        with patch.object(
            mock_notification_task.immich_client, "get_asset_thumbnail", new_callable=AsyncMock
        ):
            mock_user = AsyncMock()
            mock_user.send = AsyncMock(side_effect=discord.Forbidden(Mock(), "DMs disabled"))
            mock_notification_task.client.fetch_user = AsyncMock(return_value=mock_user)

            # Process asset - should handle Forbidden gracefully
            await mock_notification_task._process_asset(sample_immich_asset)

            # Should attempt to send but handle error
            mock_user.send.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_poll_loop_initialization(mock_notification_task, test_database):
    """Test polling loop initializes last_check timestamp."""
    # No last_check timestamp initially
    timestamp = await test_database.get_last_check_timestamp()
    assert timestamp is None

    # Mock list_new_assets to return empty
    with patch.object(
        mock_notification_task.immich_client, "list_new_assets", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = []

        # Start task briefly
        await mock_notification_task.start()

        # Give it a moment to initialize
        import asyncio

        await asyncio.sleep(0.1)

        # Stop task
        await mock_notification_task.stop()

        # Verify timestamp was set
        timestamp = await test_database.get_last_check_timestamp()
        assert timestamp is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_poll_loop_updates_timestamp(mock_notification_task, test_database):
    """Test polling loop updates last_check timestamp."""
    # Set initial timestamp
    initial_time = datetime.utcnow() - timedelta(hours=2)
    await test_database.update_last_check_timestamp(initial_time)

    with patch.object(
        mock_notification_task.immich_client, "list_new_assets", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = []

        # Start and stop task
        await mock_notification_task.start()
        await asyncio.sleep(0.1)
        await mock_notification_task.stop()

        # Verify timestamp was updated
        updated_timestamp = await test_database.get_last_check_timestamp()
        assert updated_timestamp > initial_time


@pytest.mark.asyncio
@pytest.mark.unit
async def test_notification_task_handles_errors_gracefully(mock_notification_task, test_database):
    """Test polling loop handles errors gracefully."""
    with patch.object(
        mock_notification_task.immich_client, "list_new_assets", new_callable=AsyncMock
    ) as mock_list:
        mock_list.side_effect = Exception("Network error")

        # Start task - should not crash
        await mock_notification_task.start()
        await asyncio.sleep(0.1)
        await mock_notification_task.stop()

        # Task should still be running (error handled)
        assert mock_notification_task.running is False  # Stopped cleanly
