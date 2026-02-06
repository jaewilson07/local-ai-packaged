"""Persona capability schemas.

Pydantic models for personality, character configuration, and state management.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# Personality/State Models
class SeedPreferences(BaseModel):
    """Initial preferences that can be overridden by memory over time."""

    communication_style: str = Field(
        default="friendly and helpful",
        description="How the bot communicates (formal, casual, witty, etc.)",
    )
    topics_of_interest: list[str] = Field(
        default_factory=list, description="Topics the bot is naturally drawn to discuss"
    )
    emoji_usage: str = Field(
        default="moderate",
        description="How often the bot uses emojis (never, rare, moderate, frequent)",
    )
    formality: str = Field(default="balanced", description="Level of formality in responses")


class Personality(BaseModel):
    """Complete personality definition for a chatbot persona."""

    id: str = Field(..., description="Unique lowercase identifier")
    name: str = Field(..., description="Display name")
    byline: str = Field(default="", description="Short description")
    identity: list[str] = Field(default_factory=list, description="Core traits that never change")
    behavior: list[str] = Field(default_factory=list, description="Response style guidelines")
    seed_preferences: SeedPreferences = Field(
        default_factory=SeedPreferences,
        description="Starting preferences (can be overridden by memory)",
    )
    profile_image: str | None = Field(default=None, description="Optional image path or URL")


class PersonaState(BaseModel):
    """Complete state of a persona including memory and mood."""

    personality: Personality
    mood: str = Field(default="neutral", description="Current mood (happy, sad, excited, etc.)")
    mood_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    relationship_feeling: str = Field(default="neutral", description="How persona feels about user")
    recently_mentioned_topics: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.now)


# Discord Character Models
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


class ChatRequest(BaseModel):
    """Request to generate a character response."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")
    user_id: str = Field(..., description="Discord user ID")
    message: str = Field(..., description="User message content")
    message_id: str | None = Field(None, description="Discord message ID")


class ChatResponse(BaseModel):
    """Response with character message."""

    message: str
    mood: str
    relationship_feeling: str


class EngageRequest(BaseModel):
    """Request to check engagement opportunity."""

    channel_id: str = Field(..., description="Discord channel ID")
    character_id: str = Field(..., description="Character identifier")


class EngageResponse(BaseModel):
    """Response indicating whether to engage."""

    should_engage: bool
    message: str | None = None
    confidence: float


__all__ = [
    # Personality/State
    "SeedPreferences",
    "Personality",
    "PersonaState",
    # Discord Character
    "AddCharacterRequest",
    "RemoveCharacterRequest",
    "ListCharactersRequest",
    "ChatRequest",
    "ChatResponse",
    "EngageRequest",
    "EngageResponse",
]
