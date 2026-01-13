"""Tests for /claim_face command in UploadCapability."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.capabilities.upload import PersonSelectView, UploadCapability
from bot.immich_client import ImmichClient
from discord import app_commands


@pytest.fixture
def upload_capability_with_database(mock_discord_client, mock_immich_client, test_database):
    """Create UploadCapability instance with database for testing."""
    return UploadCapability(
        client=mock_discord_client, immich_client=mock_immich_client, database=test_database
    )


@pytest.fixture
def mock_command_tree_for_decorator():
    """Create a mock command tree that properly captures decorated functions."""
    tree = MagicMock(spec=app_commands.CommandTree)

    # Store registered commands
    tree._registered_commands = {}

    def command_decorator(**kwargs):
        """Return a decorator that captures the function."""

        def decorator(func):
            tree._registered_commands[kwargs.get("name", func.__name__)] = func
            return func

        return decorator

    tree.command = MagicMock(side_effect=command_decorator)
    tree.sync = AsyncMock(return_value=[])
    return tree


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_single_result(
    upload_capability_with_database,
    mock_discord_interaction,
    sample_immich_people,
    mock_command_tree_for_decorator,
):
    """Test /claim_face command with single search result."""
    capability = upload_capability_with_database
    single_person = [sample_immich_people[0]]

    with patch.object(
        capability.immich_client, "search_people", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = single_person

        # Setup command via capability on_ready
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get the registered command function
        assert "claim_face" in mock_command_tree_for_decorator._registered_commands
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

        # Execute command
        await command_func(mock_discord_interaction, search_name="John")

        # Verify search was called
        mock_search.assert_called_once_with("John")

        # Verify database save was called
        user = await capability.database.get_user_by_discord_id(
            str(mock_discord_interaction.user.id)
        )
        assert user is not None
        assert user["immich_person_id"] == single_person[0]["id"]

        # Verify response sent
        mock_discord_interaction.response.defer.assert_called_once()
        mock_discord_interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_multiple_results(
    upload_capability_with_database,
    mock_discord_interaction,
    sample_immich_people,
    mock_command_tree_for_decorator,
):
    """Test /claim_face command with multiple search results."""
    capability = upload_capability_with_database

    with patch.object(
        capability.immich_client, "search_people", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = sample_immich_people

        # Setup command via capability on_ready
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get the registered command function
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

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
    upload_capability_with_database, mock_discord_interaction, mock_command_tree_for_decorator
):
    """Test /claim_face command with no search results."""
    capability = upload_capability_with_database

    with patch.object(
        capability.immich_client, "search_people", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = []

        # Setup command via capability on_ready
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get the registered command function
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

        # Execute command
        await command_func(mock_discord_interaction, search_name="NonExistent")

        # Verify error message sent
        mock_discord_interaction.followup.send.assert_called_once()
        call_args = mock_discord_interaction.followup.send.call_args[0][0]
        assert "no people found" in call_args.lower() or "not found" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_api_error(
    upload_capability_with_database, mock_discord_interaction, mock_command_tree_for_decorator
):
    """Test /claim_face command handles API errors."""
    capability = upload_capability_with_database

    with patch.object(
        capability.immich_client, "search_people", new_callable=AsyncMock
    ) as mock_search:
        mock_search.side_effect = Exception("API connection error")

        # Setup command via capability on_ready
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get the registered command function
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

        # Execute command
        await command_func(mock_discord_interaction, search_name="Test")

        # Verify error message sent
        mock_discord_interaction.followup.send.assert_called_once()
        call_args = mock_discord_interaction.followup.send.call_args[0][0]
        assert "error" in call_args.lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_claim_face_disabled_without_database(
    mock_discord_client, mock_immich_client, mock_command_tree
):
    """Test /claim_face is not registered when database is not provided."""
    # Create capability without database
    capability = UploadCapability(
        client=mock_discord_client, immich_client=mock_immich_client, database=None
    )

    # on_ready should not register the command
    await capability.on_ready(mock_command_tree)

    # tree.command should not have been called
    mock_command_tree.command.assert_not_called()


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

    # Replace the select_menu with a mock that has controllable values
    mock_select = MagicMock()
    mock_select.values = [sample_immich_people[0]["id"]]
    view.select_menu = mock_select

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

    # Replace the select_menu with a mock that has empty values
    mock_select = MagicMock()
    mock_select.values = []
    view.select_menu = mock_select

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

    # Replace the select_menu with a mock that has invalid selection
    mock_select = MagicMock()
    mock_select.values = ["invalid_person_id"]
    view.select_menu = mock_select

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
    many_people = [{"id": f"person{i}", "name": f"Person {i}"} for i in range(30)]

    mock_immich_client = AsyncMock(spec=ImmichClient)

    view = PersonSelectView(
        people=many_people,
        immich_client=mock_immich_client,
        database=test_database,
        user_id="123456789",
    )

    # Should only have 25 options (Discord limit)
    assert len(view.select_menu.options) == 25
