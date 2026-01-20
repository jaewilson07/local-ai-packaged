---
name: discord-bot-development
description: Guide Discord bot development with discord.py, capability-based architecture, and testing. Use when building Discord bots, creating slash commands, handling messages, implementing cogs/capabilities, or when the user asks about bot testing, background tasks, or MCP integration.
---

# Discord Bot Development

Best practices for building Discord bots using discord.py, following this project's capability-based architecture from `03-apps/discord-bot/`.

## Architecture Overview

```
bot/
├── main.py                 # Entry point, client setup
├── config.py               # Configuration from environment
├── database.py             # SQLite database wrapper
├── capabilities/           # Modular feature system
│   ├── __init__.py         # CapabilityRegistry
│   ├── base.py             # BaseCapability class
│   ├── echo.py             # Simple echo capability
│   ├── upload.py           # File upload capability
│   └── character.py        # Character AI capability
├── handlers/               # Event handlers
│   ├── command_handler.py
│   ├── upload_handler.py
│   └── notification_task.py
├── agents/                 # Background agents
│   ├── base.py             # BaseAgent class
│   ├── manager.py          # AgentManager
│   └── bluesky_agent.py    # Social media agent
├── mcp/                    # MCP server integration
│   ├── server.py
│   └── tools/
└── api_client.py           # Lambda API client
tests/
├── conftest.py             # Shared fixtures
├── unit/                   # Unit tests
├── integration/            # Integration tests
└── manual/                 # Manual test scripts
```

## Capability-Based Architecture

### Base Capability

All capabilities inherit from `BaseCapability`:

```python
from abc import ABC, abstractmethod
import discord
from discord import app_commands

class BaseCapability(ABC):
    """Base class for bot capabilities."""

    name: str = "base"
    description: str = "Base capability"
    priority: int = 100  # Lower = higher priority

    def __init__(self, client: discord.Client, settings: dict | None = None):
        self.client = client
        self.settings = settings or {}

    @abstractmethod
    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """Called when bot is ready. Register commands here."""
        pass

    @abstractmethod
    async def handle_message(self, message: discord.Message) -> bool:
        """
        Handle a message.

        Returns:
            True if message was handled, False to continue chain
        """
        pass

    async def cleanup(self) -> None:
        """Clean up resources on shutdown."""
        pass
```

### Capability Registry

```python
class CapabilityRegistry:
    """Registry for managing bot capabilities."""

    def __init__(self, client: discord.Client):
        self.client = client
        self.capabilities: list[BaseCapability] = []

    def register(self, capability: BaseCapability) -> None:
        """Register a capability."""
        self.capabilities.append(capability)
        # Sort by priority
        self.capabilities.sort(key=lambda c: c.priority)

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """Initialize all capabilities."""
        for cap in self.capabilities:
            await cap.on_ready(tree)

    async def handle_message(self, message: discord.Message) -> bool:
        """Route message through capability chain."""
        for cap in self.capabilities:
            if await cap.handle_message(message):
                return True  # Message handled, stop chain
        return False

    async def cleanup(self) -> None:
        """Clean up all capabilities."""
        for cap in self.capabilities:
            await cap.cleanup()
```

### Implementing a Capability

```python
import discord
from discord import app_commands
from .base import BaseCapability

class MyCapability(BaseCapability):
    """My custom capability."""

    name = "my_capability"
    description = "Does something useful"
    priority = 50  # Medium priority

    def __init__(
        self,
        client: discord.Client,
        api_client: APIClient | None = None,
        settings: dict | None = None,
    ):
        super().__init__(client, settings)
        self.api_client = api_client

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """Register slash commands."""

        @tree.command(name="mycommand", description="My command")
        async def my_command(interaction: discord.Interaction, arg: str):
            await interaction.response.defer()

            result = await self.process(arg)

            await interaction.followup.send(result)

        # Register with tree
        tree.command()(my_command)

    async def handle_message(self, message: discord.Message) -> bool:
        """Handle messages if needed."""
        # Check if this capability should handle the message
        if not message.content.startswith("!my"):
            return False  # Let other capabilities handle it

        # Process the message
        await message.reply("Processed!")
        return True  # Message handled

    async def process(self, data: str) -> str:
        """Process data using API."""
        if self.api_client:
            return await self.api_client.process(data)
        return "No API client configured"
```

## Slash Commands

### Basic Command

```python
from discord import app_commands

@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    """Simple ping command."""
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency}ms")
```

### Command with Arguments

```python
@tree.command(name="search", description="Search for content")
@app_commands.describe(
    query="What to search for",
    limit="Maximum results (default: 5)"
)
async def search(
    interaction: discord.Interaction,
    query: str,
    limit: int = 5,
):
    """Search command with arguments."""
    await interaction.response.defer()  # For long operations

    results = await perform_search(query, limit)

    if not results:
        await interaction.followup.send("No results found.")
        return

    embed = discord.Embed(title=f"Results for: {query}")
    for r in results:
        embed.add_field(name=r.title, value=r.summary, inline=False)

    await interaction.followup.send(embed=embed)
```

### Command with Choices

```python
from typing import Literal

@tree.command(name="mode", description="Set operation mode")
async def set_mode(
    interaction: discord.Interaction,
    mode: Literal["fast", "balanced", "thorough"],
):
    """Command with predefined choices."""
    await interaction.response.send_message(f"Mode set to: {mode}")
```

## Message Handling

### Basic Message Handler

```python
@client.event
async def on_message(message: discord.Message):
    """Handle incoming messages."""
    # Ignore bot messages
    if message.author.bot:
        return

    # Route through capability registry
    handled = await capability_registry.handle_message(message)

    if not handled:
        # Default behavior or logging
        pass
```

### Handling Attachments

```python
async def handle_upload(message: discord.Message) -> bool:
    """Handle file uploads."""
    if not message.attachments:
        return False

    for attachment in message.attachments:
        # Check file type
        if not attachment.content_type.startswith("image/"):
            continue

        # Check file size (e.g., 10MB limit)
        if attachment.size > 10 * 1024 * 1024:
            await message.reply("File too large (max 10MB)")
            continue

        # Download file
        file_data = await attachment.read()

        # Process file
        result = await process_file(file_data, attachment.filename)

        await message.reply(f"Processed: {result}")

    return True
```

## Background Tasks

### Using tasks.loop

```python
from discord.ext import tasks

class NotificationTask:
    """Background task for notifications."""

    def __init__(self, client: discord.Client, database: Database):
        self.client = client
        self.database = database
        self._task = None

    async def start(self):
        """Start the background task."""
        self._task = self.check_notifications.start()

    async def stop(self):
        """Stop the background task."""
        if self._task:
            self.check_notifications.cancel()

    @tasks.loop(minutes=5)
    async def check_notifications(self):
        """Check for pending notifications."""
        try:
            notifications = await self.database.get_pending_notifications()

            for notif in notifications:
                channel = self.client.get_channel(notif.channel_id)
                if channel:
                    await channel.send(notif.message)
                    await self.database.mark_sent(notif.id)

        except Exception as e:
            logger.exception(f"Error in notification task: {e}")

    @check_notifications.before_loop
    async def before_check(self):
        """Wait for bot to be ready."""
        await self.client.wait_until_ready()
```

## Agent Pattern

For complex background processes, use the Agent pattern:

```python
from abc import ABC, abstractmethod
import asyncio

class BaseAgent(ABC):
    """Base class for background agents."""

    name: str = "base"

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self.discord_client: discord.Client | None = None

    def set_discord_client(self, client: discord.Client):
        """Set Discord client for sending messages."""
        self.discord_client = client

    async def start(self):
        """Start the agent."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the agent."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self):
        """Main agent loop."""
        while self._running:
            try:
                await self.process()
            except Exception as e:
                logger.exception(f"Agent {self.name} error: {e}")
            await asyncio.sleep(self.interval)

    @property
    @abstractmethod
    def interval(self) -> int:
        """Interval between runs in seconds."""
        pass

    @abstractmethod
    async def process(self):
        """Main processing logic."""
        pass

    async def send_to_channel(self, channel_id: int, content: str):
        """Send message to Discord channel."""
        if self.discord_client:
            channel = self.discord_client.get_channel(channel_id)
            if channel:
                await channel.send(content)
```

## Configuration

```python
import os
from dataclasses import dataclass

@dataclass
class BotConfig:
    """Bot configuration from environment."""

    # Required
    DISCORD_BOT_TOKEN: str
    DISCORD_UPLOAD_CHANNEL_ID: int

    # Optional with defaults
    MCP_ENABLED: bool = False
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8080

    # API integration
    LAMBDA_API_URL: str | None = None
    LAMBDA_API_KEY: str | None = None

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load config from environment."""
        return cls(
            DISCORD_BOT_TOKEN=os.environ["DISCORD_BOT_TOKEN"],
            DISCORD_UPLOAD_CHANNEL_ID=int(os.environ["DISCORD_UPLOAD_CHANNEL_ID"]),
            MCP_ENABLED=os.environ.get("MCP_ENABLED", "").lower() == "true",
            LAMBDA_API_URL=os.environ.get("LAMBDA_API_URL"),
            LAMBDA_API_KEY=os.environ.get("LAMBDA_API_KEY"),
        )

    def validate(self) -> list[str]:
        """Validate configuration."""
        errors = []
        if not self.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not self.DISCORD_UPLOAD_CHANNEL_ID:
            errors.append("DISCORD_UPLOAD_CHANNEL_ID is required")
        return errors

config = BotConfig.from_env()
```

## Testing

### Mock Fixtures

```python
import pytest
from unittest.mock import AsyncMock, Mock
import discord

@pytest.fixture
def mock_discord_client():
    """Mock Discord Client."""
    client = AsyncMock(spec=discord.Client)
    client.user = Mock()
    client.user.id = 999999999
    client.user.name = "TestBot"
    return client

@pytest.fixture
def mock_discord_message(mock_discord_user, mock_discord_channel):
    """Mock Discord Message."""
    message = AsyncMock(spec=discord.Message)
    message.author = mock_discord_user
    message.channel = mock_discord_channel
    message.content = "Test message"
    message.attachments = []
    message.reply = AsyncMock()
    return message

@pytest.fixture
def mock_discord_interaction(mock_discord_user):
    """Mock Discord Interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = mock_discord_user
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction
```

### Testing Commands

```python
@pytest.mark.asyncio
async def test_ping_command(mock_discord_interaction, mock_discord_client):
    """Test ping command."""
    mock_discord_client.latency = 0.05  # 50ms

    await ping.callback(mock_discord_interaction)

    mock_discord_interaction.response.send_message.assert_awaited_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "50ms" in call_args[0][0]
```

### Testing Capabilities

```python
@pytest.mark.asyncio
async def test_capability_handles_message(
    mock_discord_client,
    mock_discord_message,
):
    """Test capability message handling."""
    capability = MyCapability(mock_discord_client)

    mock_discord_message.content = "!mycommand test"

    handled = await capability.handle_message(mock_discord_message)

    assert handled is True
    mock_discord_message.reply.assert_awaited_once()
```

## Additional Resources

- [testing-patterns.md](testing-patterns.md) - Discord-specific mock fixtures
- [capability-template.md](capability-template.md) - Base capability implementation
