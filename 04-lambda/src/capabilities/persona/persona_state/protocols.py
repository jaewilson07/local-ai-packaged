"""Protocols for persona domain backends."""

from typing import Protocol

from capabilities.persona.persona_state.models import (
    ActivePersona,
    ConversationContext,
    MoodState,
    Personality,
    RelationshipState,
)


class PersonaStore(Protocol):
    """Protocol for swappable persona backends."""

    def get_personality(self, persona_id: str) -> Personality | None:
        """Load personality by ID."""
        ...

    def list_personalities(self) -> list[str]:
        """List available personality IDs."""
        ...

    def get_active_persona(self, interface: str = "cli") -> ActivePersona | None:
        """Get active persona for interface."""
        ...

    def set_active_persona(self, persona_id: str, interface: str = "cli") -> bool:
        """Set active persona for interface."""
        ...

    def get_mood(self, user_id: str, persona_id: str) -> MoodState | None:
        """Get current mood state."""
        ...

    def update_mood(self, user_id: str, persona_id: str, mood: MoodState) -> None:
        """Update mood state."""
        ...

    def get_relationship(self, user_id: str, persona_id: str) -> RelationshipState | None:
        """Get relationship state with user."""
        ...

    def update_relationship(
        self, user_id: str, persona_id: str, relationship: RelationshipState
    ) -> None:
        """Update relationship state."""
        ...

    def get_conversation_context(self, user_id: str, persona_id: str) -> ConversationContext | None:
        """Get current conversation context."""
        ...

    def update_conversation_context(
        self, user_id: str, persona_id: str, context: ConversationContext
    ) -> None:
        """Update conversation context."""
        ...
