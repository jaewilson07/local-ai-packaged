"""Pydantic models for persona state and personality definitions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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

    def build_system_prompt(self, memory_overrides: dict[str, Any] | None = None) -> str:
        """Build a system prompt from identity, behavior, and preferences."""
        sections = []

        sections.append(f"You are {self.name}. {self.byline}")

        if self.identity:
            sections.append("\n## Who You Are")
            for trait in self.identity:
                sections.append(f"- {trait}")

        if self.behavior:
            sections.append("\n## How You Behave")
            for guideline in self.behavior:
                sections.append(f"- {guideline}")

        effective_prefs = self.seed_preferences.model_dump()
        if memory_overrides:
            effective_prefs.update(memory_overrides)

        sections.append("\n## Your Preferences")
        sections.append(
            f"- Communication style: {effective_prefs.get('communication_style', 'friendly')}"
        )
        sections.append(f"- Formality: {effective_prefs.get('formality', 'balanced')}")

        topics = effective_prefs.get("topics_of_interest", [])
        if topics:
            sections.append(f"- Topics you enjoy: {', '.join(topics)}")

        emoji = effective_prefs.get("emoji_usage", "moderate")
        if emoji == "never":
            sections.append("- Never use emojis in responses")
        elif emoji == "rare":
            sections.append("- Rarely use emojis, only when truly appropriate")
        elif emoji == "moderate":
            sections.append("- Use emojis moderately, when they add value to the conversation")
        elif emoji == "frequent":
            sections.append("- Feel free to use emojis to express yourself")

        return "\n".join(sections)


class ActivePersona(BaseModel):
    """Tracks which personality is active for each interface."""

    cli: str = Field(default="jarvis", description="Active persona ID for CLI")
    discord: str = Field(default="alex", description="Active persona ID for Discord")


class MoodState(BaseModel):
    """Current emotional state of persona."""

    primary_emotion: str = Field(
        ..., description="Primary emotion (happy, sad, excited, neutral, etc.)"
    )
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity from 0.0 to 1.0")
    timestamp: datetime = Field(default_factory=datetime.now)


class RelationshipState(BaseModel):
    """Relationship level with specific user."""

    user_id: str = Field(..., description="User identifier")
    persona_id: str = Field(..., description="Persona identifier")
    affection_score: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Affection level from -1.0 to 1.0"
    )
    trust_level: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Trust level from 0.0 to 1.0"
    )
    interaction_count: int = Field(default=0, description="Number of interactions")
    last_interaction: datetime | None = Field(
        default=None, description="Last interaction timestamp"
    )


class ConversationContext(BaseModel):
    """Current conversation mode/context."""

    mode: str = Field(
        default="balanced",
        description="Conversation mode (deep_empathy, casual_chat, storytelling, balanced_factual, balanced)",
    )
    topic: str | None = Field(default=None, description="Current conversation topic")
    depth_level: int = Field(default=3, ge=1, le=5, description="Conversation depth level from 1-5")


class PersonaState(BaseModel):
    """Complete stateful persona representation."""

    base_profile: Personality = Field(..., description="Base personality from JSON")
    current_mood: MoodState = Field(..., description="Current emotional state")
    relationships: dict[str, RelationshipState] = Field(
        default_factory=dict, description="Relationships keyed by user_id"
    )
    current_context: ConversationContext = Field(..., description="Current conversation context")
    learned_preferences: dict[str, Any] = Field(
        default_factory=dict, description="Learned preferences from memory"
    )


# API Request/Response Models
class GetVoiceInstructionsRequest(BaseModel):
    """Request to get voice instructions."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")


class RecordInteractionRequest(BaseModel):
    """Request to record an interaction."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    user_message: str = Field(..., description="User's message")
    bot_response: str = Field(..., description="Bot's response")


class GetPersonaStateRequest(BaseModel):
    """Request to get persona state."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")


class UpdateMoodRequest(BaseModel):
    """Request to update mood."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    primary_emotion: str = Field(..., description="Primary emotion")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity")


class VoiceInstructionsResponse(BaseModel):
    """Response with voice instructions."""

    success: bool = Field(..., description="Whether the operation was successful")
    voice_instructions: str = Field(..., description="Generated voice/style instructions")


class PersonaStateResponse(BaseModel):
    """Response with persona state."""

    success: bool = Field(..., description="Whether the operation was successful")
    persona_state: PersonaState = Field(..., description="Current persona state")
