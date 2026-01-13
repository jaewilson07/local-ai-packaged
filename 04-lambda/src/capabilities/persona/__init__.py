"""Persona capability - Character personality and state management."""

from .ai import (
    PersonaAgentState,
    PersonaDeps,
    get_persona_state,
    persona_agent,
    update_persona_mood,
)
from .persona_workflow import character_chat_workflow, update_persona_mood_workflow
from .router import get_persona_deps, router
from .schemas import (
    AddCharacterRequest,
    ChatRequest,
    ChatResponse,
    EngageRequest,
    EngageResponse,
    ListCharactersRequest,
    Personality,
    PersonaState,
    RemoveCharacterRequest,
    SeedPreferences,
)

__all__ = [
    # Router
    "router",
    "get_persona_deps",
    # Workflows
    "character_chat_workflow",
    "update_persona_mood_workflow",
    # AI
    "PersonaDeps",
    "PersonaAgentState",
    "persona_agent",
    "update_persona_mood",
    "get_persona_state",
    # Schemas
    "SeedPreferences",
    "Personality",
    "PersonaState",
    "AddCharacterRequest",
    "RemoveCharacterRequest",
    "ListCharactersRequest",
    "ChatRequest",
    "ChatResponse",
    "EngageRequest",
    "EngageResponse",
]
