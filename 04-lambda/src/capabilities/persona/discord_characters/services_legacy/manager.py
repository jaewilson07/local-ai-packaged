"""Manager for Discord character channel operations."""

from .models import ChannelCharacter, CharacterMessage
from .store import DiscordCharacterStore


class DiscordCharacterManager:
    """Manages Discord character operations."""

    def __init__(self, store: DiscordCharacterStore):
        """Initialize with a store."""
        self.store = store

    async def close(self):
        """Close the store connection."""
        await self.store.close()

    async def add_character(
        self, channel_id: str, character_id: str, persona_id: str
    ) -> tuple[bool, str]:
        """
        Add a character to a channel.

        Returns:
            (success, message)
        """
        # Check channel limit (5 characters max)
        existing = await self.store.list_channel_characters(channel_id)
        if len(existing) >= 5:
            return False, "Channel already has the maximum of 5 characters"

        # Check if character already exists
        if any(c.character_id == character_id for c in existing):
            return False, f"Character '{character_id}' is already in this channel"

        success = await self.store.add_character_to_channel(channel_id, character_id, persona_id)

        if success:
            return True, f"Character '{character_id}' added to channel"
        return False, f"Failed to add character '{character_id}'"

    async def remove_character(self, channel_id: str, character_id: str) -> tuple[bool, str]:
        """
        Remove a character from a channel.

        Returns:
            (success, message)
        """
        success = await self.store.remove_character_from_channel(channel_id, character_id)

        if success:
            # Clear conversation history for this character
            await self.store.clear_channel_history(channel_id, character_id)
            return True, f"Character '{character_id}' removed from channel"
        return False, f"Character '{character_id}' not found in channel"

    async def list_characters(self, channel_id: str) -> list[ChannelCharacter]:
        """List all characters in a channel."""
        return await self.store.list_channel_characters(channel_id)

    async def get_character(self, channel_id: str, character_id: str) -> ChannelCharacter | None:
        """Get a specific character in a channel."""
        return await self.store.get_channel_character(channel_id, character_id)

    async def record_message(self, message: CharacterMessage):
        """Record a message in the conversation history."""
        await self.store.add_message(message)

        # Update message count if it's an assistant message
        if message.role == "assistant":
            await self.store.increment_message_count(message.channel_id, message.character_id)

    async def get_conversation_context(
        self, channel_id: str, character_id: str, limit: int = 20
    ) -> list[CharacterMessage]:
        """Get recent conversation messages for context."""
        return await self.store.get_recent_messages(channel_id, character_id, limit)

    async def clear_history(
        self, channel_id: str, character_id: str | None = None
    ) -> tuple[bool, str]:
        """
        Clear conversation history.

        Returns:
            (success, message)
        """
        await self.store.clear_channel_history(channel_id, character_id)

        if character_id:
            return True, f"History cleared for character '{character_id}' in channel"
        return True, "History cleared for all characters in channel"
