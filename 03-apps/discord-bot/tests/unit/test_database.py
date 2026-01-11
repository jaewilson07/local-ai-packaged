"""Tests for database operations."""

from datetime import datetime

import pytest


@pytest.mark.asyncio
@pytest.mark.unit
async def test_database_initialization(test_database):
    """Test database initialization creates required tables."""
    # Database should be initialized by fixture
    # Verify we can query tables
    import aiosqlite

    async with aiosqlite.connect(test_database.db_path) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            assert "users" in tables
            assert "last_check" in tables


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_user_mapping(test_database):
    """Test saving user mapping."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    user = await test_database.get_user_by_discord_id("123456789")
    assert user is not None
    assert user["discord_id"] == "123456789"
    assert user["immich_person_id"] == "person1"
    assert user["notify_enabled"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_user_by_discord_id(test_database):
    """Test retrieving user by Discord ID."""
    # Save a user first
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    user = await test_database.get_user_by_discord_id("123456789")
    assert user is not None
    assert user["discord_id"] == "123456789"

    # Test non-existent user
    user = await test_database.get_user_by_discord_id("999999999")
    assert user is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_user_by_immich_person_id(test_database):
    """Test retrieving user by Immich person ID."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    user = await test_database.get_user_by_immich_person_id("person1")
    assert user is not None
    assert user["immich_person_id"] == "person1"

    # Test with notify_enabled=False (should not return)
    await test_database.save_user_mapping(
        discord_id="999999999",
        immich_person_id="person2",
        notify_enabled=False,
    )

    user = await test_database.get_user_by_immich_person_id("person2")
    assert user is None  # Should not return disabled notifications


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_notify_enabled(test_database):
    """Test updating notification preference."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    # Disable notifications
    await test_database.update_notify_enabled("123456789", False)

    user = await test_database.get_user_by_discord_id("123456789")
    assert user["notify_enabled"] == 0

    # Re-enable notifications
    await test_database.update_notify_enabled("123456789", True)

    user = await test_database.get_user_by_discord_id("123456789")
    assert user["notify_enabled"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_last_check_timestamp(test_database):
    """Test last check timestamp management."""
    # Initially should be None
    timestamp = await test_database.get_last_check_timestamp()
    assert timestamp is None

    # Set timestamp
    now = datetime.utcnow()
    await test_database.update_last_check_timestamp(now)

    # Retrieve timestamp
    retrieved = await test_database.get_last_check_timestamp()
    assert retrieved is not None
    assert isinstance(retrieved, datetime)

    # Update timestamp
    later = datetime.utcnow()
    await test_database.update_last_check_timestamp(later)

    retrieved = await test_database.get_last_check_timestamp()
    assert retrieved >= now


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_user_mapping_updates_existing(test_database):
    """Test that save_user_mapping updates existing records."""
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person1",
        notify_enabled=True,
    )

    # Update with new person ID
    await test_database.save_user_mapping(
        discord_id="123456789",
        immich_person_id="person2",
        notify_enabled=True,
    )

    user = await test_database.get_user_by_discord_id("123456789")
    assert user["immich_person_id"] == "person2"  # Should be updated


@pytest.mark.asyncio
@pytest.mark.unit
async def test_multiple_users(test_database):
    """Test handling multiple users."""
    await test_database.save_user_mapping("user1", "person1", True)
    await test_database.save_user_mapping("user2", "person2", True)
    await test_database.save_user_mapping("user3", "person3", False)

    user1 = await test_database.get_user_by_discord_id("user1")
    user2 = await test_database.get_user_by_discord_id("user2")
    user3 = await test_database.get_user_by_discord_id("user3")

    assert user1["immich_person_id"] == "person1"
    assert user2["immich_person_id"] == "person2"
    assert user3["immich_person_id"] == "person3"

    # Only enabled users should be returned by get_user_by_immich_person_id
    person1_user = await test_database.get_user_by_immich_person_id("person1")
    person2_user = await test_database.get_user_by_immich_person_id("person2")
    person3_user = await test_database.get_user_by_immich_person_id("person3")

    assert person1_user is not None
    assert person2_user is not None
    assert person3_user is None  # notify_enabled=False
