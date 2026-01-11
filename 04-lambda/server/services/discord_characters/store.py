"""Storage interface for Discord character data."""

from datetime import datetime
from typing import Any

from pymongo import AsyncMongoClient

from .models import ChannelCharacter, CharacterMessage


class DiscordCharacterStore:
    """MongoDB store for Discord character data."""

    def __init__(self, mongodb_url: str, db_name: str = "localai", db: Any | None = None):
        """
        Initialize MongoDB connection.

        Args:
            mongodb_url: MongoDB connection URL
            db_name: Database name
            db: Optional existing database instance (for dependency injection)
        """
        if db:
            self.db: Any = db
            self.client = None
        else:
            self.client = AsyncMongoClient(mongodb_url)
            self.db: Any = self.client[db_name]

        self.channel_characters = self.db["discord_channel_characters"]
        self.character_messages = self.db["discord_character_messages"]

    async def add_character_to_channel(
        self, channel_id: str, character_id: str, persona_id: str
    ) -> bool:
        """Add a character to a channel."""
        existing = await self.channel_characters.find_one(
            {"channel_id": channel_id, "character_id": character_id}
        )

        if existing:
            return False  # Already exists

        doc = {
            "channel_id": channel_id,
            "character_id": character_id,
            "persona_id": persona_id,
            "added_at": datetime.utcnow(),
            "message_count": 0,
            "last_active": None,
        }
        await self.channel_characters.insert_one(doc)
        return True

    async def remove_character_from_channel(self, channel_id: str, character_id: str) -> bool:
        """Remove a character from a channel."""
        result = await self.channel_characters.delete_one(
            {"channel_id": channel_id, "character_id": character_id}
        )
        return result.deleted_count > 0

    async def list_channel_characters(self, channel_id: str) -> list[ChannelCharacter]:
        """List all characters in a channel."""
        cursor = self.channel_characters.find({"channel_id": channel_id})
        docs = await cursor.to_list(length=None)
        return [ChannelCharacter(**doc) for doc in docs]

    async def get_channel_character(
        self, channel_id: str, character_id: str
    ) -> ChannelCharacter | None:
        """Get a specific character in a channel."""
        doc = await self.channel_characters.find_one(
            {"channel_id": channel_id, "character_id": character_id}
        )
        return ChannelCharacter(**doc) if doc else None

    async def increment_message_count(self, channel_id: str, character_id: str):
        """Increment message count for a character."""
        await self.channel_characters.update_one(
            {"channel_id": channel_id, "character_id": character_id},
            {"$inc": {"message_count": 1}, "$set": {"last_active": datetime.utcnow()}},
        )

    async def add_message(self, message: CharacterMessage) -> str:
        """Add a message to the conversation history."""
        doc = message.model_dump()
        result = await self.character_messages.insert_one(doc)
        return str(result.inserted_id)

    async def get_recent_messages(
        self, channel_id: str, character_id: str, limit: int = 20
    ) -> list[CharacterMessage]:
        """Get recent messages for a channel+character."""
        cursor = (
            self.character_messages.find({"channel_id": channel_id, "character_id": character_id})
            .sort("timestamp", -1)
            .limit(limit)
        )

        docs = await cursor.to_list(length=limit)
        return [CharacterMessage(**doc) for doc in reversed(docs)]  # Reverse to chronological order

    async def clear_channel_history(self, channel_id: str, character_id: str | None = None):
        """Clear conversation history for a channel (optionally for a specific character)."""
        query = {"channel_id": channel_id}
        if character_id:
            query["character_id"] = character_id

        await self.character_messages.delete_many(query)

    async def get_all_channels_with_characters(self) -> list[str]:
        """Get all channel IDs that have active characters."""
        channels = await self.channel_characters.distinct("channel_id")
        return list(channels)

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            await self.client.close()
