"""Integration tests for /claim_face workflow via UploadCapability."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bot.capabilities.upload import PersonSelectView, UploadCapability
from bot.immich_client import ImmichClient
from discord import app_commands


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
@pytest.mark.integration
async def test_full_claim_face_flow_single_result(
    test_database,
    mock_discord_interaction,
    mock_discord_client,
    sample_immich_people,
    mock_command_tree_for_decorator,
):
    """Test complete claim_face flow with single result via capability."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(
        client=mock_discord_client, immich_client=immich_client, database=test_database
    )
    single_person = [sample_immich_people[0]]

    with patch.object(immich_client, "search_people", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = single_person

        # Setup command via capability
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get command handler from registered commands
        assert "claim_face" in mock_command_tree_for_decorator._registered_commands
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

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
    test_database,
    mock_discord_interaction,
    mock_discord_client,
    sample_immich_people,
    mock_command_tree_for_decorator,
):
    """Test complete claim_face flow with multiple results via capability."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(
        client=mock_discord_client, immich_client=immich_client, database=test_database
    )

    with patch.object(immich_client, "search_people", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_immich_people

        # Setup command via capability
        await capability.on_ready(mock_command_tree_for_decorator)

        # Get command handler from registered commands
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]

        # Execute command
        await command_func(mock_discord_interaction, search_name="John")

        # Verify select menu was sent
        call_kwargs = mock_discord_interaction.followup.send.call_args[1]
        assert "view" in call_kwargs

        view = call_kwargs["view"]
        assert isinstance(view, PersonSelectView)

        # Simulate user selection by replacing select_menu with mock
        mock_select = MagicMock()
        mock_select.values = [sample_immich_people[0]["id"]]
        view.select_menu = mock_select
        await view._on_select(mock_discord_interaction)

        # Verify database was updated
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user is not None
        assert user["immich_person_id"] == sample_immich_people[0]["id"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_claim_face_flow_updates_existing_mapping(
    test_database,
    mock_discord_interaction,
    mock_discord_client,
    sample_immich_people,
    mock_command_tree_for_decorator,
):
    """Test claim_face updates existing user mapping via capability."""
    # Create initial mapping
    await test_database.save_user_mapping(
        discord_id=str(mock_discord_interaction.user.id),
        immich_person_id="old_person_id",
        notify_enabled=True,
    )

    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(
        client=mock_discord_client, immich_client=immich_client, database=test_database
    )
    single_person = [sample_immich_people[0]]

    with patch.object(immich_client, "search_people", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = single_person

        # Setup and execute command via capability
        await capability.on_ready(mock_command_tree_for_decorator)
        command_func = mock_command_tree_for_decorator._registered_commands["claim_face"]
        await command_func(mock_discord_interaction, search_name="John")

        # Verify mapping was updated
        user = await test_database.get_user_by_discord_id(str(mock_discord_interaction.user.id))
        assert user["immich_person_id"] == single_person[0]["id"]  # Updated, not old_person_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_capability_registers_command_in_tree(
    test_database, mock_discord_client, mock_command_tree
):
    """Test UploadCapability registers /claim_face in command tree."""
    immich_client = ImmichClient(base_url="http://test:2283", api_key="test-key")
    capability = UploadCapability(
        client=mock_discord_client, immich_client=immich_client, database=test_database
    )

    await capability.on_ready(mock_command_tree)

    # Verify tree.command was called with correct parameters
    mock_command_tree.command.assert_called_once()
    call_kwargs = mock_command_tree.command.call_args[1]
    assert call_kwargs["name"] == "claim_face"
    assert "description" in call_kwargs
