"""Persona agent for character interaction and state management."""

# Import directly from submodules to avoid circular imports
from app.capabilities.persona.ai.dependencies import PersonaDeps
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from app.core.llm import get_llm_model


class PersonaAgentState(BaseModel):
    """Shared state for persona agents."""


# Create the persona agent
persona_agent = Agent(
    get_llm_model(),
    deps_type=PersonaDeps,
    system_prompt=(
        "You are an expert in character personality management and interaction. "
        "You help maintain consistent personalities with evolving moods and relationships. "
        "Always provide thoughtful, in-character responses that reflect the persona's traits."
    ),
)


@persona_agent.tool
async def update_persona_mood(
    ctx: RunContext[PersonaDeps],
    persona_id: str,
    new_mood: str,
    confidence: float = 0.5,
) -> str:
    """
    Update the mood of a persona.

    This tool updates the current mood and mood confidence for a persona,
    affecting how they interact.

    Args:
        ctx: Agent runtime context with dependencies
        persona_id: Unique persona identifier
        new_mood: New mood state (happy, sad, excited, confused, etc.)
        confidence: Confidence in the mood (0.0-1.0)

    Returns:
        String confirming the mood update
    """
    # Import here to avoid circular dependencies
    from capabilities.persona.persona_state.tools import update_mood

    deps = ctx.deps
    if not deps.db:
        await deps.initialize()

    await update_mood(ctx, persona_id, new_mood, confidence)
    return f"Updated {persona_id}'s mood to '{new_mood}' with confidence {confidence:.2f}"


@persona_agent.tool
async def get_persona_state(
    ctx: RunContext[PersonaDeps],
    persona_id: str,
) -> str:
    """
    Retrieve the current state of a persona.

    This tool fetches the complete persona state including personality,
    mood, mood confidence, and relationship information.

    Args:
        ctx: Agent runtime context with dependencies
        persona_id: Unique persona identifier

    Returns:
        String describing the persona's current state
    """
    # Import here to avoid circular dependencies
    from capabilities.persona.persona_state.tools import get_state

    deps = ctx.deps
    if not deps.db:
        await deps.initialize()

    result = await get_state(ctx, persona_id)
    return f"Persona state for {persona_id}: mood={result['mood']}, relationship={result['relationship_feeling']}"


__all__ = [
    "PersonaAgentState",
    "get_persona_state",
    "persona_agent",
    "update_persona_mood",
]
