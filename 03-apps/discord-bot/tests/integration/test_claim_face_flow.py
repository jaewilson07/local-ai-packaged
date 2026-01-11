"""Integration tests for claim_face workflow."""

import pytest
from unittest.mock import AsyncMock, patch
from bot.handlers.command_handler import setup_claim_face_command
from bot.immich_client import ImmichClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_claim_face_flow_single_result(
    test_database, mock_discord_interaction, sample_immich_people
):
    """Test complete claim_face flow with single result."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    single_person = [sample_immich_people[0]]
    
    with patch.object(immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = single_person
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, immich_client, test_database)
        
        # Get command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="John")
        
        # Verify search was called
        mock_search.assert_called_once_with("John")
        
        # Verify database was updated
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user is not None
        assert user["immich_person_id"] == single_person[0]["id"]
        assert user["notify_enabled"] == 1
        
        # Verify response sent
        mock_discord_interaction.followup.send.assert_called_once()
        response_text = mock_discord_interaction.followup.send.call_args[0][0]
        assert "found one match" in response_text.lower() or "linked" in response_text.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_claim_face_flow_multiple_results(
    test_database, mock_discord_interaction, sample_immich_people
):
    """Test complete claim_face flow with multiple results."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    
    with patch.object(immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_immich_people
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, immich_client, test_database)
        
        # Get command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="John")
        
        # Verify select menu was sent
        call_kwargs = mock_discord_interaction.followup.send.call_args[1]
        assert "view" in call_kwargs
        
        # Simulate selection
        from bot.handlers.command_handler import PersonSelectView
        view = call_kwargs["view"]
        assert isinstance(view, PersonSelectView)
        
        # Simulate user selection
        view.select_menu.values = [sample_immich_people[0]["id"]]
        await view._on_select(mock_discord_interaction)
        
        # Verify database was updated
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user is not None
        assert user["immich_person_id"] == sample_immich_people[0]["id"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_claim_face_flow_updates_existing_mapping(
    test_database, mock_discord_interaction, sample_immich_people
):
    """Test claim_face updates existing user mapping."""
    # Create initial mapping
    await test_database.save_user_mapping(
        discord_id=str(mock_discord_interaction.user.id),
        immich_person_id="old_person_id",
        notify_enabled=True,
    )
    
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    single_person = [sample_immich_people[0]]
    
    with patch.object(immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = single_person
        
        # Setup and execute command
        tree = AsyncMock()
        await setup_claim_face_command(tree, immich_client, test_database)
        command_func = tree.command.call_args[0][1]
        await command_func(mock_discord_interaction, search_name="John")
        
        # Verify mapping was updated
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user["immich_person_id"] == single_person[0]["id"]  # Updated, not old_person_id
