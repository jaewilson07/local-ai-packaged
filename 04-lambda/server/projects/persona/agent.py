"""Main Persona agent implementation."""

import logging
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import Optional
from pydantic_ai.ag_ui import StateDeps

from server.projects.shared.llm import get_llm_model
from server.projects.persona.config import config
from server.projects.persona.dependencies import PersonaDeps
from server.projects.persona.tools import get_voice_instructions, record_interaction

logger = logging.getLogger(__name__)


class PersonaAgentState(BaseModel):
    """Minimal shared state for the Persona agent."""
    pass


# System prompt for persona agent
PERSONA_SYSTEM_PROMPT = """You are a persona management assistant that helps manage chatbot personas.

You can:
- Generate voice/style instructions based on persona state
- Record interactions to update mood, relationship, and context
- Get current persona state
- Update persona mood and relationship

Voice instructions help guide how a persona should respond based on their current emotional state,
relationship with the user, and conversation context.
"""


# Create the Persona agent with AGUI support
persona_agent = Agent(
    get_llm_model(),
    deps_type=PersonaDeps,
    system_prompt=PERSONA_SYSTEM_PROMPT
)


# Register tools
@persona_agent.tool
async def get_persona_voice_instructions_tool(
    ctx: RunContext[PersonaDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
) -> str:
    """
    Generate dynamic style instructions based on current persona state.
    
    Returns prompt injection with current emotional state, relationship context,
    and conversation mode to guide persona responses.
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    return await get_voice_instructions(deps, user_id, persona_id)


@persona_agent.tool
async def record_persona_interaction_tool(
    ctx: RunContext[PersonaDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    user_message: str = Field(..., description="User's message"),
    bot_response: str = Field(..., description="Bot's response"),
) -> str:
    """
    Record an interaction to update persona state (mood, relationship, context).
    
    Automatically analyzes the interaction and updates:
    - Mood state based on emotional tone
    - Relationship state based on sentiment
    - Conversation context based on mode and topic
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    result = await record_interaction(deps, user_id, persona_id, user_message, bot_response)
    return f"Interaction recorded. Mood: {result.get('mood', {}).get('primary_emotion', 'unknown')}, Relationship: {result.get('relationship', {}).get('affection_score', 0):.2f}"


@persona_agent.tool
async def get_persona_state_tool(
    ctx: RunContext[PersonaDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
) -> str:
    """
    Get current persona state including mood, relationship, and context.
    
    Returns formatted persona state information.
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    if not deps.persona_store:
        return "Persona store not initialized"
    
    # Get all state components
    personality = deps.persona_store.get_personality(persona_id)
    mood = deps.persona_store.get_mood(user_id, persona_id)
    relationship = deps.persona_store.get_relationship(user_id, persona_id)
    context = deps.persona_store.get_conversation_context(user_id, persona_id)
    
    parts = []
    if personality:
        parts.append(f"Persona: {personality.name} ({personality.id})")
        parts.append(f"Byline: {personality.byline}")
    
    if mood:
        parts.append(f"\nMood: {mood.primary_emotion} (intensity: {mood.intensity:.2f})")
    
    if relationship:
        parts.append(f"\nRelationship:")
        parts.append(f"  - Affection: {relationship.affection_score:.2f}")
        parts.append(f"  - Trust: {relationship.trust_level:.2f}")
        parts.append(f"  - Interactions: {relationship.interaction_count}")
    
    if context:
        parts.append(f"\nContext:")
        parts.append(f"  - Mode: {context.mode}")
        parts.append(f"  - Topic: {context.topic or 'None'}")
        parts.append(f"  - Depth: {context.depth_level}/5")
    
    return "\n".join(parts) if parts else "No persona state found"


@persona_agent.tool
async def update_persona_mood_tool(
    ctx: RunContext[PersonaDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    primary_emotion: str = Field(..., description="Primary emotion"),
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity"),
) -> str:
    """
    Update persona mood state.
    
    Manually set the persona's current emotional state.
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    if not deps.persona_store:
        return "Persona store not initialized"
    
    from server.projects.persona.models import MoodState
    from datetime import datetime
    
    mood = MoodState(
        primary_emotion=primary_emotion,
        intensity=intensity,
        timestamp=datetime.now()
    )
    
    deps.persona_store.update_mood(user_id, persona_id, mood)
    return f"Mood updated: {primary_emotion} (intensity: {intensity:.2f})"
