"""Request/response models for Discord character API."""

from pydantic import BaseModel, Field


class AddCharacterRequest(BaseModel):
    """Request to add a character to a channel."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    persona_id: str = Field(..., description="Persona ID from persona service")


class RemoveCharacterRequest(BaseModel):
    """Request to remove a character from a channel."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")


class ListCharactersRequest(BaseModel):
    """Request to list characters in a channel."""

    channel_id: str = Field(..., description="Discord channel ID")


class ClearHistoryRequest(BaseModel):
    """Request to clear conversation history."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str | None = Field(
        None, description="Optional character ID to clear specific character"
    )


class ChatRequest(BaseModel):
    """Request to generate a character response."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    user_id: str = Field(..., description="Discord user ID")
    message: str = Field(..., description="User message content")
    message_id: str | None = Field(None, description="Discord message ID")


class EngageRequest(BaseModel):
    """Request to check engagement opportunity."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    recent_messages: list[str] = Field(..., description="Recent channel messages for context")


class CharacterResponse(BaseModel):
    """Response with character information."""

    channel_id: str
    character_id: str
    persona_id: str
    name: str | None = None
    byline: str | None = None
    profile_image: str | None = None


class ChatResponse(BaseModel):
    """Response from character chat."""

    success: bool
    response: str
    character_id: str
    character_name: str | None = None


class EngageResponse(BaseModel):
    """Response from engagement check."""

    should_engage: bool
    response: str | None = None
    character_id: str
