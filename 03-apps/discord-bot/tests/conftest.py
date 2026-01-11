"""Shared pytest fixtures for Discord bot tests."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest
from discord import app_commands

# Set minimal environment variables before any imports
os.environ.setdefault("DISCORD_BOT_TOKEN", "test-token")
os.environ.setdefault("DISCORD_UPLOAD_CHANNEL_ID", "987654321")  # Match test expectations
os.environ.setdefault("IMMICH_API_KEY", "test-api-key")
os.environ.setdefault("IMMICH_SERVER_URL", "http://test-immich:2283")
os.environ.setdefault("BOT_DB_PATH", "/tmp/test_bot.sqlite")

from bot.database import Database
from bot.immich_client import ImmichClient


# Discord.py Mock Fixtures
@pytest.fixture
def mock_discord_client():
    """Mock Discord Client."""
    client = AsyncMock(spec=discord.Client)
    client.user = Mock()
    client.user.id = 999999999
    client.user.name = "TestBot"
    client.close = AsyncMock()
    client.start = AsyncMock()
    client.fetch_user = AsyncMock()
    return client


@pytest.fixture
def mock_discord_user():
    """Mock Discord User."""
    user = AsyncMock(spec=discord.User)
    user.id = 123456789
    user.name = "TestUser"
    user.display_name = "TestUser"
    user.send = AsyncMock()
    return user


@pytest.fixture
def mock_discord_channel():
    """Mock Discord Channel."""
    channel = Mock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.name = "event-uploads"
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_discord_message(mock_discord_user, mock_discord_channel):
    """Mock Discord Message object."""
    message = AsyncMock(spec=discord.Message)
    message.id = 111222333
    message.author = mock_discord_user
    message.channel = mock_discord_channel
    message.attachments = []
    message.reply = AsyncMock()
    message.add_reaction = AsyncMock()
    message.content = "Test message"
    return message


@pytest.fixture
def mock_discord_attachment():
    """Mock Discord Attachment."""
    attachment = Mock()
    attachment.id = 444555666
    attachment.filename = "test.jpg"
    attachment.size = 1024 * 1024  # 1MB
    attachment.read = AsyncMock(return_value=b"fake_image_data")
    attachment.content_type = "image/jpeg"
    return attachment


@pytest.fixture
def mock_discord_interaction(mock_discord_user):
    """Mock Discord Interaction."""
    interaction = AsyncMock(spec=app_commands.Interaction)
    interaction.id = 777888999
    interaction.user = mock_discord_user
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_command_tree():
    """Mock CommandTree."""
    tree = AsyncMock(spec=app_commands.CommandTree)
    tree.sync = AsyncMock(return_value=[])
    return tree


# Immich Client Mock Fixtures
@pytest.fixture
def mock_immich_response():
    """Mock aiohttp response for Immich API."""
    response = AsyncMock()
    response.status = 200
    response.raise_for_status = AsyncMock()
    response.json = AsyncMock(return_value={"id": "asset123"})
    return response


@pytest.fixture
def mock_immich_client(mock_immich_response):
    """Mock ImmichClient with aiohttp responses."""
    client = ImmichClient(base_url="http://test-immich:2283", api_key="test-key")

    # Mock aiohttp ClientSession
    mock_session = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_context.post = AsyncMock(return_value=mock_immich_response)
    mock_context.get = AsyncMock(return_value=mock_immich_response)
    mock_session.return_value = mock_context

    with patch("aiohttp.ClientSession", return_value=mock_context):
        yield client


@pytest.fixture
def sample_immich_people():
    """Sample Immich people data."""
    return [
        {"id": "person1", "name": "John Doe", "thumbnailPath": "/thumb1.jpg"},
        {"id": "person2", "name": "Jane Smith", "thumbnailPath": "/thumb2.jpg"},
        {"id": "person3", "name": "John Smith", "thumbnailPath": "/thumb3.jpg"},
    ]


@pytest.fixture
def sample_immich_asset():
    """Sample Immich asset data."""
    return {
        "id": "asset123",
        "type": "IMAGE",
        "originalPath": "/path/to/image.jpg",
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_immich_faces():
    """Sample Immich face detection data."""
    return [
        {"id": "face1", "personId": "person1", "assetId": "asset123"},
        {"id": "face2", "personId": "person2", "assetId": "asset123"},
    ]


# Database Fixtures
@pytest.fixture
async def test_database(tmp_path):
    """Create test database with temporary path."""
    db_path = tmp_path / "test_bot.sqlite"
    db = Database(db_path=str(db_path))
    await db.initialize()
    yield db
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_user_mapping():
    """Sample user mapping data."""
    return {
        "discord_id": "123456789",
        "immich_person_id": "person1",
        "notify_enabled": True,
    }


# File Fixtures
@pytest.fixture
def sample_image_data():
    """Sample image file data."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb"


@pytest.fixture
def sample_video_data():
    """Sample video file data."""
    return b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom"


# Notification Task Fixtures
@pytest.fixture
def mock_notification_task(mock_discord_client, mock_immich_client, test_database):
    """Mock NotificationTask."""
    from bot.handlers.notification_task import NotificationTask

    task = NotificationTask(
        client=mock_discord_client,
        immich_client=mock_immich_client,
        database=test_database,
    )
    return task


# MCP Server Fixtures
@pytest.fixture
def mock_mcp_server():
    """Mock MCP server."""
    server = AsyncMock()
    server.http_app = Mock(return_value=Mock())
    return server


# Config Fixtures
@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration with test values."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    monkeypatch.setenv("DISCORD_UPLOAD_CHANNEL_ID", "987654321")
    monkeypatch.setenv("IMMICH_API_KEY", "test-api-key")
    monkeypatch.setenv("IMMICH_SERVER_URL", "http://test-immich:2283")
    monkeypatch.setenv("BOT_DB_PATH", "/tmp/test_bot.sqlite")
    monkeypatch.setenv("NOTIFICATION_POLL_INTERVAL", "120")
    monkeypatch.setenv("MCP_ENABLED", "false")

    # Reload config after env changes
    import importlib

    from bot import config

    importlib.reload(config)
    yield config


# Utility Fixtures
@pytest.fixture
def mock_time(monkeypatch):
    """Mock datetime for time-dependent tests."""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)

    class MockDatetime:
        @staticmethod
        def utcnow():
            return fixed_time

        @staticmethod
        def now():
            return fixed_time

    monkeypatch.setattr("datetime.datetime", MockDatetime)
    return fixed_time
