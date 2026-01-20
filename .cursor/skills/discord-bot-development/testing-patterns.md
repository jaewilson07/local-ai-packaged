# Discord Bot Testing Patterns

Comprehensive testing patterns for Discord bots using pytest and AsyncMock.

## Core Mock Fixtures

### Discord Client

```python
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
import discord
from discord import app_commands

@pytest.fixture
def mock_discord_client():
    """Mock Discord Client with common attributes."""
    client = AsyncMock(spec=discord.Client)
    client.user = Mock()
    client.user.id = 999999999
    client.user.name = "TestBot"
    client.user.discriminator = "0001"
    client.latency = 0.05  # 50ms

    # Mock common methods
    client.close = AsyncMock()
    client.start = AsyncMock()
    client.fetch_user = AsyncMock()
    client.get_channel = Mock(return_value=None)
    client.get_guild = Mock(return_value=None)

    # Mock wait_until_ready for background tasks
    client.wait_until_ready = AsyncMock()

    return client

@pytest.fixture
def mock_command_tree():
    """Mock CommandTree for slash commands."""
    tree = MagicMock(spec=app_commands.CommandTree)
    tree.sync = AsyncMock(return_value=[])
    tree.command = MagicMock()  # Decorator
    return tree
```

### Discord User

```python
@pytest.fixture
def mock_discord_user():
    """Mock Discord User."""
    user = AsyncMock(spec=discord.User)
    user.id = 123456789
    user.name = "TestUser"
    user.display_name = "TestUser"
    user.discriminator = "1234"
    user.bot = False
    user.send = AsyncMock()
    user.mention = "<@123456789>"
    return user

@pytest.fixture
def mock_bot_user():
    """Mock bot user (for filtering bot messages)."""
    user = AsyncMock(spec=discord.User)
    user.id = 999999999
    user.name = "TestBot"
    user.bot = True
    return user
```

### Discord Channel

```python
@pytest.fixture
def mock_text_channel():
    """Mock Discord TextChannel."""
    channel = Mock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "test-channel"
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    channel.history = AsyncMock()
    channel.mention = "<#987654321>"
    return channel

@pytest.fixture
def mock_dm_channel():
    """Mock Discord DMChannel."""
    channel = AsyncMock(spec=discord.DMChannel)
    channel.id = 111222333
    channel.send = AsyncMock()
    return channel
```

### Discord Message

```python
@pytest.fixture
def mock_discord_message(mock_discord_user, mock_text_channel):
    """Mock Discord Message."""
    message = AsyncMock(spec=discord.Message)
    message.id = 111222333444
    message.author = mock_discord_user
    message.channel = mock_text_channel
    message.guild = Mock()
    message.guild.id = 555666777

    # Content
    message.content = "Test message content"
    message.clean_content = "Test message content"

    # Attachments
    message.attachments = []

    # Actions
    message.reply = AsyncMock()
    message.add_reaction = AsyncMock()
    message.delete = AsyncMock()
    message.edit = AsyncMock()

    # Mentions
    message.mentions = []
    message.role_mentions = []
    message.channel_mentions = []

    return message
```

### Discord Attachment

```python
@pytest.fixture
def mock_attachment():
    """Mock Discord Attachment."""
    attachment = Mock(spec=discord.Attachment)
    attachment.id = 444555666
    attachment.filename = "test_image.jpg"
    attachment.size = 1024 * 100  # 100KB
    attachment.content_type = "image/jpeg"
    attachment.url = "https://cdn.discordapp.com/attachments/test.jpg"
    attachment.read = AsyncMock(return_value=b"fake_image_data")
    return attachment

@pytest.fixture
def mock_large_attachment():
    """Mock large attachment for size limit testing."""
    attachment = Mock(spec=discord.Attachment)
    attachment.filename = "large_file.zip"
    attachment.size = 50 * 1024 * 1024  # 50MB
    attachment.content_type = "application/zip"
    return attachment
```

### Discord Interaction

```python
@pytest.fixture
def mock_discord_interaction(mock_discord_user, mock_text_channel):
    """Mock Discord Interaction for slash commands."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.id = 777888999
    interaction.user = mock_discord_user
    interaction.channel = mock_text_channel
    interaction.guild = Mock()
    interaction.guild.id = 555666777

    # Response handling
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.send_modal = AsyncMock()
    interaction.response.is_done = Mock(return_value=False)

    # Followup for deferred responses
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()

    # Edit original
    interaction.edit_original_response = AsyncMock()
    interaction.delete_original_response = AsyncMock()

    return interaction
```

### Discord Guild and Member

```python
@pytest.fixture
def mock_guild():
    """Mock Discord Guild (server)."""
    guild = Mock(spec=discord.Guild)
    guild.id = 555666777
    guild.name = "Test Server"
    guild.owner_id = 123456789
    guild.get_member = Mock(return_value=None)
    guild.fetch_member = AsyncMock()
    return guild

@pytest.fixture
def mock_member(mock_discord_user, mock_guild):
    """Mock Discord Member (user in a guild)."""
    member = AsyncMock(spec=discord.Member)
    member.id = mock_discord_user.id
    member.name = mock_discord_user.name
    member.display_name = "Server Nickname"
    member.guild = mock_guild
    member.roles = []
    member.send = AsyncMock()
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member
```

## Testing Patterns

### Testing Slash Commands

```python
@pytest.mark.asyncio
async def test_slash_command_basic(mock_discord_interaction):
    """Test basic slash command execution."""
    # Call the command callback directly
    await my_command.callback(mock_discord_interaction)

    # Verify response was sent
    mock_discord_interaction.response.send_message.assert_awaited_once()

@pytest.mark.asyncio
async def test_slash_command_with_defer(mock_discord_interaction):
    """Test command that defers response."""
    # Mark response as done after defer
    mock_discord_interaction.response.is_done = Mock(return_value=True)

    await slow_command.callback(mock_discord_interaction, arg="test")

    # Verify defer was called
    mock_discord_interaction.response.defer.assert_awaited_once()

    # Verify followup was used
    mock_discord_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_slash_command_with_embed(mock_discord_interaction):
    """Test command that sends an embed."""
    await info_command.callback(mock_discord_interaction)

    call_args = mock_discord_interaction.response.send_message.call_args
    assert "embed" in call_args.kwargs

    embed = call_args.kwargs["embed"]
    assert isinstance(embed, discord.Embed)
```

### Testing Message Handlers

```python
@pytest.mark.asyncio
async def test_message_handler_ignores_bots(
    mock_discord_message,
    mock_bot_user,
):
    """Test that bot messages are ignored."""
    mock_discord_message.author = mock_bot_user

    # Handler should return early
    result = await handle_message(mock_discord_message)

    # No reply should be sent
    mock_discord_message.reply.assert_not_awaited()

@pytest.mark.asyncio
async def test_message_handler_processes_command(mock_discord_message):
    """Test message command processing."""
    mock_discord_message.content = "!mycommand arg1 arg2"

    await handle_message(mock_discord_message)

    mock_discord_message.reply.assert_awaited_once()
    reply_content = mock_discord_message.reply.call_args[0][0]
    assert "processed" in reply_content.lower()

@pytest.mark.asyncio
async def test_message_handler_with_mention(
    mock_discord_message,
    mock_discord_client,
):
    """Test handling messages that mention the bot."""
    mock_discord_message.content = "<@999999999> hello"
    mock_discord_message.mentions = [mock_discord_client.user]

    await handle_message(mock_discord_message)

    mock_discord_message.reply.assert_awaited()
```

### Testing Capabilities

```python
@pytest.mark.asyncio
async def test_capability_registration(mock_discord_client):
    """Test capability registration."""
    registry = CapabilityRegistry(mock_discord_client)
    capability = MyCapability(mock_discord_client)

    registry.register(capability)

    assert len(registry.capabilities) == 1
    assert registry.capabilities[0].name == "my_capability"

@pytest.mark.asyncio
async def test_capability_priority_ordering(mock_discord_client):
    """Test capabilities are ordered by priority."""
    registry = CapabilityRegistry(mock_discord_client)

    low_priority = MyCapability(mock_discord_client)
    low_priority.priority = 100

    high_priority = ImportantCapability(mock_discord_client)
    high_priority.priority = 10

    registry.register(low_priority)
    registry.register(high_priority)

    # High priority should be first
    assert registry.capabilities[0].priority == 10

@pytest.mark.asyncio
async def test_capability_handles_message(
    mock_discord_client,
    mock_discord_message,
):
    """Test capability message handling."""
    capability = MyCapability(mock_discord_client)

    mock_discord_message.content = "!mycap test"

    handled = await capability.handle_message(mock_discord_message)

    assert handled is True

@pytest.mark.asyncio
async def test_capability_passes_unhandled(
    mock_discord_client,
    mock_discord_message,
):
    """Test capability passes unhandled messages."""
    capability = MyCapability(mock_discord_client)

    mock_discord_message.content = "random message"

    handled = await capability.handle_message(mock_discord_message)

    assert handled is False
```

### Testing Background Tasks

```python
@pytest.mark.asyncio
async def test_background_task_starts(mock_discord_client):
    """Test background task starts correctly."""
    task = NotificationTask(mock_discord_client, database=Mock())

    await task.start()

    assert task._task is not None

@pytest.mark.asyncio
async def test_background_task_waits_for_ready(mock_discord_client):
    """Test task waits for bot to be ready."""
    task = NotificationTask(mock_discord_client, database=Mock())

    # Simulate the before_loop callback
    await task.check_notifications.before_loop()

    mock_discord_client.wait_until_ready.assert_awaited_once()

@pytest.mark.asyncio
async def test_background_task_processes(
    mock_discord_client,
    mock_text_channel,
):
    """Test background task processing."""
    mock_discord_client.get_channel = Mock(return_value=mock_text_channel)

    database = AsyncMock()
    database.get_pending_notifications = AsyncMock(return_value=[
        Mock(id=1, channel_id=987654321, message="Test notification")
    ])
    database.mark_sent = AsyncMock()

    task = NotificationTask(mock_discord_client, database)

    # Call process method directly
    await task.check_notifications()

    mock_text_channel.send.assert_awaited_once_with("Test notification")
    database.mark_sent.assert_awaited_once_with(1)
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_command_handles_api_error(mock_discord_interaction):
    """Test command handles API errors gracefully."""
    # Mock API to raise error
    with patch("bot.api_client.APIClient.process") as mock_api:
        mock_api.side_effect = ConnectionError("API unavailable")

        await my_command.callback(mock_discord_interaction, data="test")

        # Should send error message
        call_args = mock_discord_interaction.followup.send.call_args
        assert "error" in call_args[0][0].lower()

@pytest.mark.asyncio
async def test_capability_handles_exception(
    mock_discord_client,
    mock_discord_message,
    caplog,
):
    """Test capability logs exceptions."""
    capability = BrokenCapability(mock_discord_client)

    # Should not raise, but should log
    await capability.handle_message(mock_discord_message)

    assert "error" in caplog.text.lower()
```

### Testing with Database

```python
@pytest.fixture
async def test_database(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.sqlite"
    db = Database(str(db_path))
    await db.initialize()
    yield db
    # Cleanup handled by tmp_path

@pytest.mark.asyncio
async def test_database_operations(test_database):
    """Test database CRUD operations."""
    # Create
    await test_database.add_user_mapping(
        discord_id="123",
        immich_person_id="person_1",
    )

    # Read
    mapping = await test_database.get_user_mapping("123")
    assert mapping is not None
    assert mapping["immich_person_id"] == "person_1"

    # Delete
    await test_database.remove_user_mapping("123")
    mapping = await test_database.get_user_mapping("123")
    assert mapping is None
```

## Advanced Patterns

### Testing Concurrent Operations

```python
@pytest.mark.asyncio
async def test_concurrent_message_handling():
    """Test handling multiple messages concurrently."""
    capability = MyCapability(mock_discord_client)

    messages = [create_mock_message(f"message {i}") for i in range(10)]

    # Process all concurrently
    results = await asyncio.gather(
        *[capability.handle_message(msg) for msg in messages]
    )

    assert all(r is True for r in results)

def create_mock_message(content: str) -> Mock:
    """Factory for creating mock messages."""
    message = AsyncMock(spec=discord.Message)
    message.content = content
    message.author = Mock(bot=False)
    message.reply = AsyncMock()
    return message
```

### Testing with Real Discord Objects

```python
@pytest.mark.asyncio
async def test_with_real_embed():
    """Test with real Discord Embed object."""
    embed = discord.Embed(
        title="Test",
        description="Test description",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Field 1", value="Value 1")

    assert embed.title == "Test"
    assert len(embed.fields) == 1
```

### Parameterized Testing

```python
@pytest.mark.parametrize("content,should_handle", [
    ("!command arg", True),
    ("!command", True),
    ("random text", False),
    ("", False),
    ("!other_command", False),
])
@pytest.mark.asyncio
async def test_message_handling_variants(
    mock_discord_message,
    content,
    should_handle,
):
    """Test various message content handling."""
    mock_discord_message.content = content

    result = await capability.handle_message(mock_discord_message)

    assert result == should_handle
```
