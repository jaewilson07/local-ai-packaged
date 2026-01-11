"""Request/response models for Discord character API."""

from typing import Optional, List
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
    character_id: Optional[str] = Field(None, description="Optional character ID to clear specific character")


class ChatRequest(BaseModel):
    """Request to generate a character response."""
    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    user_id: str = Field(..., description="Discord user ID")
    message: str = Field(..., description="User message content")
    message_id: Optional[str] = Field(None, description="Discord message ID")


class EngageRequest(BaseModel):
    """Request to check engagement opportunity."""
    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    recent_messages: List[str] = Field(..., description="Recent channel messages for context")


class CharacterResponse(BaseModel):
    """Response with character information."""
    channel_id: str
    character_id: str
    persona_id: str
    name: Optional[str] = None
    byline: Optional[str] = None
    profile_image: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from character chat."""
    success: bool
    response: str
    character_id: str
    character_name: Optional[str] = None


class EngageResponse(BaseModel):
    """Response from engagement check."""
    should_engage: bool
    response: Optional[str] = None
    character_id: str
