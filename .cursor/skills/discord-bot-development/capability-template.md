# Capability Template

Template for implementing new Discord bot capabilities.

## Base Capability Class

```python
from abc import ABC, abstractmethod
import logging
import discord
from discord import app_commands

logger = logging.getLogger(__name__)


class BaseCapability(ABC):
    """
    Base class for bot capabilities.

    Capabilities are modular features that can:
    - Register slash commands
    - Handle messages
    - Manage their own state and cleanup
    """

    # Capability metadata
    name: str = "base"
    description: str = "Base capability"
    priority: int = 100  # Lower number = higher priority

    def __init__(
        self,
        client: discord.Client,
        settings: dict | None = None,
    ):
        """
        Initialize capability.

        Args:
            client: Discord client instance
            settings: Optional per-capability settings from API
        """
        self.client = client
        self.settings = settings or {}
        self._commands_registered = False

    @abstractmethod
    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when bot is ready. Register commands here.

        Args:
            tree: Command tree for registering slash commands
        """
        pass

    @abstractmethod
    async def handle_message(self, message: discord.Message) -> bool:
        """
        Handle an incoming message.

        Args:
            message: The Discord message to handle

        Returns:
            True if the message was handled (stops chain),
            False to pass to next capability
        """
        pass

    async def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        pass

    def get_setting(self, key: str, default=None):
        """Get a capability setting with default."""
        return self.settings.get(key, default)
```

## Complete Capability Example

```python
"""Example capability implementation."""

import logging
import discord
from discord import app_commands

from .base import BaseCapability
from bot.api_client import APIClient

logger = logging.getLogger(__name__)


class ExampleCapability(BaseCapability):
    """
    Example capability demonstrating all patterns.

    Features:
    - Slash command registration
    - Message handling with prefix
    - External API integration
    - Error handling
    """

    name = "example"
    description = "Example capability for demonstration"
    priority = 50  # Medium priority

    def __init__(
        self,
        client: discord.Client,
        api_client: APIClient | None = None,
        settings: dict | None = None,
    ):
        super().__init__(client, settings)
        self.api_client = api_client
        self.command_prefix = self.get_setting("prefix", "!example")

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """Register slash commands."""
        if self._commands_registered:
            return

        # Define the slash command
        @tree.command(
            name="example",
            description="Example command"
        )
        @app_commands.describe(
            query="What to process",
            verbose="Show detailed output"
        )
        async def example_command(
            interaction: discord.Interaction,
            query: str,
            verbose: bool = False,
        ):
            await self._handle_slash_command(interaction, query, verbose)

        self._commands_registered = True
        logger.info(f"Registered commands for {self.name} capability")

    async def _handle_slash_command(
        self,
        interaction: discord.Interaction,
        query: str,
        verbose: bool,
    ) -> None:
        """Handle the slash command execution."""
        # Defer for potentially long operation
        await interaction.response.defer()

        try:
            # Process the request
            if self.api_client:
                result = await self.api_client.process(query)
            else:
                result = f"Processed locally: {query}"

            # Build response
            if verbose:
                embed = discord.Embed(
                    title="Example Result",
                    description=result,
                    color=discord.Color.green(),
                )
                embed.add_field(name="Query", value=query)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(result)

        except Exception as e:
            logger.exception(f"Error in example command: {e}")
            await interaction.followup.send(
                f"An error occurred: {e}",
                ephemeral=True,
            )

    async def handle_message(self, message: discord.Message) -> bool:
        """Handle messages with prefix."""
        # Check for prefix
        if not message.content.startswith(self.command_prefix):
            return False

        # Parse command and args
        parts = message.content[len(self.command_prefix):].strip().split()
        if not parts:
            await message.reply(f"Usage: {self.command_prefix} <subcommand>")
            return True

        subcommand = parts[0].lower()
        args = parts[1:]

        # Route to subcommand handlers
        handlers = {
            "help": self._handle_help,
            "info": self._handle_info,
            "process": self._handle_process,
        }

        handler = handlers.get(subcommand)
        if handler:
            await handler(message, args)
            return True

        await message.reply(
            f"Unknown subcommand: {subcommand}\n"
            f"Available: {', '.join(handlers.keys())}"
        )
        return True

    async def _handle_help(
        self,
        message: discord.Message,
        args: list[str],
    ) -> None:
        """Handle help subcommand."""
        help_text = f"""
**{self.name.title()} Capability**
{self.description}

**Commands:**
- `{self.command_prefix} help` - Show this help
- `{self.command_prefix} info` - Show status
- `{self.command_prefix} process <data>` - Process data
- `/example <query>` - Slash command version
"""
        await message.reply(help_text)

    async def _handle_info(
        self,
        message: discord.Message,
        args: list[str],
    ) -> None:
        """Handle info subcommand."""
        status = "Connected" if self.api_client else "Local only"
        await message.reply(f"Status: {status}")

    async def _handle_process(
        self,
        message: discord.Message,
        args: list[str],
    ) -> None:
        """Handle process subcommand."""
        if not args:
            await message.reply("Please provide data to process")
            return

        data = " ".join(args)

        # Add reaction to show processing
        await message.add_reaction("⏳")

        try:
            if self.api_client:
                result = await self.api_client.process(data)
            else:
                result = f"Processed: {data}"

            await message.remove_reaction("⏳", self.client.user)
            await message.add_reaction("✅")
            await message.reply(result)

        except Exception as e:
            await message.remove_reaction("⏳", self.client.user)
            await message.add_reaction("❌")
            await message.reply(f"Error: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info(f"Cleaning up {self.name} capability")
        # Close any connections, cancel tasks, etc.
```

## Capability Registration

```python
# In main.py
def load_capabilities(
    enabled: list[str] | None = None,
    capability_settings: dict[str, dict] | None = None,
) -> None:
    """Load enabled capabilities."""
    if enabled is None:
        enabled = config.get_enabled_capabilities()
    if capability_settings is None:
        capability_settings = {}

    logger.info(f"Loading capabilities: {enabled}")

    if "example" in enabled:
        from bot.capabilities.example import ExampleCapability

        settings = capability_settings.get("example", {})
        api_client = get_shared_api_client()

        capability_registry.register(
            ExampleCapability(
                client,
                api_client=api_client,
                settings=settings,
            )
        )

    # Register other capabilities...

    logger.info(f"Loaded {len(capability_registry.capabilities)} capabilities")
```

## Testing Template

```python
"""Tests for ExampleCapability."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from bot.capabilities.example import ExampleCapability


@pytest.fixture
def example_capability(mock_discord_client):
    """Create capability instance for testing."""
    return ExampleCapability(
        mock_discord_client,
        api_client=None,
        settings={"prefix": "!test"},
    )


@pytest.mark.asyncio
async def test_on_ready_registers_commands(
    example_capability,
    mock_command_tree,
):
    """Test command registration."""
    await example_capability.on_ready(mock_command_tree)

    assert example_capability._commands_registered is True


@pytest.mark.asyncio
async def test_handle_message_with_prefix(
    example_capability,
    mock_discord_message,
):
    """Test message handling with correct prefix."""
    mock_discord_message.content = "!test help"

    handled = await example_capability.handle_message(mock_discord_message)

    assert handled is True
    mock_discord_message.reply.assert_awaited()


@pytest.mark.asyncio
async def test_handle_message_without_prefix(
    example_capability,
    mock_discord_message,
):
    """Test message handling without prefix."""
    mock_discord_message.content = "random message"

    handled = await example_capability.handle_message(mock_discord_message)

    assert handled is False
    mock_discord_message.reply.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_with_api_client(
    mock_discord_client,
    mock_discord_message,
):
    """Test processing with API client."""
    api_client = AsyncMock()
    api_client.process = AsyncMock(return_value="API result")

    capability = ExampleCapability(
        mock_discord_client,
        api_client=api_client,
    )

    mock_discord_message.content = "!example process test data"

    await capability.handle_message(mock_discord_message)

    api_client.process.assert_awaited_once()


@pytest.mark.asyncio
async def test_slash_command_error_handling(
    example_capability,
    mock_discord_interaction,
):
    """Test slash command error handling."""
    example_capability.api_client = AsyncMock()
    example_capability.api_client.process.side_effect = Exception("API error")

    await example_capability._handle_slash_command(
        mock_discord_interaction,
        query="test",
        verbose=False,
    )

    # Should send error message
    call_args = mock_discord_interaction.followup.send.call_args
    assert "error" in call_args[0][0].lower()
    assert call_args.kwargs.get("ephemeral") is True
```

## Capability Checklist

When creating a new capability:

- [ ] Define `name`, `description`, and `priority` class attributes
- [ ] Implement `on_ready()` for command registration
- [ ] Implement `handle_message()` for message handling
- [ ] Implement `cleanup()` if resources need to be released
- [ ] Add proper error handling and logging
- [ ] Add user feedback (reactions, replies) for long operations
- [ ] Write unit tests for all handlers
- [ ] Document settings in capability docstring
- [ ] Add to `load_capabilities()` in main.py
