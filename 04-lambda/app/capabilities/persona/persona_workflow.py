"""Persona workflow - orchestration for character interaction and state."""

from app.capabilities.persona.ai import PersonaDeps
from app.capabilities.persona.schemas import ChatRequest, ChatResponse
from pydantic_ai import RunContext


async def character_chat_workflow(
    request: ChatRequest,
    deps: PersonaDeps | None = None,
) -> ChatResponse:
    """
    Execute character chat workflow.

    Orchestrates persona state retrieval, mood/relationship evaluation,
    and character response generation.

    Args:
        request: Chat request with character and message
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Chat response with character message and state
    """
    if deps is None:
        deps = PersonaDeps.from_settings()

    await deps.initialize()
    try:
        # Import here to avoid circular dependencies
        from capabilities.persona.discord_characters.tools import generate_response

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await generate_response(ctx, request)
        return result
    finally:
        await deps.cleanup()


async def update_persona_mood_workflow(
    persona_id: str,
    new_mood: str,
    confidence: float = 0.5,
    deps: PersonaDeps | None = None,
) -> dict[str, str]:
    """
    Execute persona mood update workflow.

    Args:
        persona_id: Unique persona identifier
        new_mood: New mood state
        confidence: Confidence in the mood (0.0-1.0)
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Result dictionary with update confirmation
    """
    if deps is None:
        deps = PersonaDeps.from_settings()

    await deps.initialize()
    try:
        from capabilities.persona.persona_state.tools import update_mood

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        await update_mood(ctx, persona_id, new_mood, confidence)
        return {"status": "success", "message": f"Updated {persona_id}'s mood to '{new_mood}'"}
    finally:
        await deps.cleanup()


__all__ = [
    "character_chat_workflow",
    "update_persona_mood_workflow",
]
