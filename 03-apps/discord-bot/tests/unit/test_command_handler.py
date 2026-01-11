"""Tests for command handler."""

import pytest
from unittest.mock import AsyncMock, patch
from bot.handlers.command_handler import setup_claim_face_command, PersonSelectView
from bot.immich_client import ImmichClient
from bot.database import Database


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_single_result(
    mock_discord_interaction, mock_immich_client, test_database, sample_immich_people
):
    """Test /claim_face command with single search result."""
    # Mock single result
    single_person = [sample_immich_people[0]]
    
    with patch.object(mock_immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = single_person
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, mock_immich_client, test_database)
        
        # Get the command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="John")
        
        # Verify search was called
        mock_search.assert_called_once_with("John")
        
        # Verify database save was called
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user is not None
        assert user["immich_person_id"] == single_person[0]["id"]
        
        # Verify response sent
        mock_discord_interaction.response.defer.assert_called_once()
        mock_discord_interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_multiple_results(
    mock_discord_interaction, mock_immich_client, test_database, sample_immich_people
):
    """Test /claim_face command with multiple search results."""
    with patch.object(mock_immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_immich_people
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, mock_immich_client, test_database)
        
        # Get the command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="John")
        
        # Verify search was called
        mock_search.assert_called_once_with("John")
        
        # Verify select menu was sent (not auto-selected)
        mock_discord_interaction.response.defer.assert_called_once()
        mock_discord_interaction.followup.send.assert_called_once()
        
        # Check that view was created
        call_kwargs = mock_discord_interaction.followup.send.call_args[1]
        assert "view" in call_kwargs
        assert isinstance(call_kwargs["view"], PersonSelectView)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_no_results(
    mock_discord_interaction, mock_immich_client, test_database
):
    """Test /claim_face command with no search results."""
    with patch.object(mock_immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, mock_immich_client, test_database)
        
        # Get the command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="NonExistent")
        
        # Verify error message sent
        mock_discord_interaction.followup.send.assert_called_once()
        call_args = mock_discord_interaction.followup.send.call_args[0][0]
        assert "no people found" in call_args.lower() or "not found" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_api_error(
    mock_discord_interaction, mock_immich_client, test_database
):
    """Test /claim_face command handles API errors."""
    with patch.object(mock_immich_client, 'search_people', new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("API connection error")
        
        # Setup command
        tree = AsyncMock()
        await setup_claim_face_command(tree, mock_immich_client, test_database)
        
        # Get the command handler
        command_func = tree.command.call_args[0][1]
        
        # Execute command
        await command_func(mock_discord_interaction, search_name="Test")
        
        # Verify error message sent
        mock_discord_interaction.followup.send.assert_called_once()
        call_args = mock_discord_interaction.followup.send.call_args[0][0]
        assert "error" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_person_select_view_selection(
    mock_discord_interaction, test_database, sample_immich_people
):
    """Test PersonSelectView selection callback."""
    mock_immich_client = AsyncMock(spec=ImmichClient)
    
    view = PersonSelectView(
        people=sample_immich_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )
    
    # Simulate selection
    view.select_menu.values = [sample_immich_people[0]["id"]]
    await view._on_select(mock_discord_interaction)
    
        # Verify database save
    user = await test_database.get_user_by_discord_id("123456789")
    assert user is not None
    assert user["immich_person_id"] == sample_immich_people[0]["id"]
    
    # Verify response sent
    mock_discord_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_person_select_view_no_selection(
    mock_discord_interaction, test_database, sample_immich_people
):
    """Test PersonSelectView with no selection."""
    mock_immich_client = AsyncMock(spec=ImmichClient)
    
    view = PersonSelectView(
        people=sample_immich_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )
    
    # Simulate empty selection
    view.select_menu.values = []
    await view._on_select(mock_discord_interaction)
    
    # Verify error message
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args[0][0]
    assert "no selection" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_person_select_view_invalid_selection(
    mock_discord_interaction, test_database, sample_immich_people
):
    """Test PersonSelectView with invalid person ID."""
    mock_immich_client = AsyncMock(spec=ImmichClient)
    
    view = PersonSelectView(
        people=sample_immich_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )
    
    # Simulate invalid selection
    view.select_menu.values = ["invalid_person_id"]
    await view._on_select(mock_discord_interaction)
    
    # Verify error message
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args[0][0]
    assert "invalid" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_person_select_view_timeout(test_database, sample_immich_people):
    """Test PersonSelectView timeout handling."""
    mock_immich_client = AsyncMock(spec=ImmichClient)
    
    view = PersonSelectView(
        people=sample_immich_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )
    
    # Simulate timeout
    await view.on_timeout()
    
    # View should be stopped
    assert view.is_finished()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_person_select_view_max_options(test_database):
    """Test PersonSelectView handles Discord's 25 option limit."""
    # Create 30 people (more than Discord's 25 limit)
    many_people = [
        {"id": f"person{i}", "name": f"Person {i}"}
        for i in range(30)
    ]
    
    mock_immich_client = AsyncMock(spec=ImmichClient)
    
    view = PersonSelectView(
        people=many_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )
    
    # Should only have 25 options (Discord limit)
    assert len(view.select_menu.options) == 25
