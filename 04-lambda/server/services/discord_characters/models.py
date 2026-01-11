"""Data models for Discord character service."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChannelCharacter(BaseModel):
    """Represents a character active in a Discord channel."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier (persona ID)")
    persona_id: str = Field(..., description="Persona ID from persona service")
    added_at: datetime = Field(
        default_factory=datetime.utcnow, description="When character was added"
    )
    message_count: int = Field(default=0, description="Number of messages from this character")
    last_active: datetime | None = Field(default=None, description="Last time character was active")


class CharacterMessage(BaseModel):
    """Represents a message in a character conversation."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    user_id: str = Field(..., description="Discord user ID who sent the message")
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    message_id: str | None = Field(default=None, description="Discord message ID")
