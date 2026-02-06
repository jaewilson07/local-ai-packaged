"""Conversation workflow orchestration.

This module provides high-level orchestration for multi-agent conversations.
"""

import logging

from app.workflows.chat.conversation.ai.dependencies import ConversationDeps
from app.workflows.chat.conversation.schemas import ConversationRequest, ConversationResponse

logger = logging.getLogger(__name__)


async def conversation_workflow(request: ConversationRequest) -> ConversationResponse:
    """
    Orchestrate a conversation workflow.

    This workflow:
    1. Initializes conversation dependencies
    2. Gets persona voice instructions
    3. Plans the response using available tools
    4. Executes tools if needed
    5. Generates final response
    6. Records interaction for persona state updates

    Args:
        request: Conversation request with user_id, persona_id, message, and context

    Returns:
        ConversationResponse with success status, response text, tools used, and mode
    """
    deps = ConversationDeps.from_settings()
    await deps.initialize()

    try:
        # Import here to avoid circular imports
        from capabilities.persona.tools import get_voice_instructions
        from workflows.chat.conversation.services.orchestrator import ConversationOrchestrator

        # Get voice instructions (unused until full orchestration is implemented)
        _voice_instructions = await get_voice_instructions(
            deps, request.user_id, request.persona_id
        )

        # Create orchestrator (unused until full orchestration is implemented)
        _orchestrator = ConversationOrchestrator(llm_client=deps.openai_client)

        # Plan response (this should call the orchestrator's planning logic)
        # For now, returning a placeholder response
        # TODO: Implement full orchestration logic using _voice_instructions and _orchestrator
        response_text = f"Received message: {request.message}"
        tools_used: list[str] = []
        mode = "balanced"

        return ConversationResponse(
            success=True, response=response_text, tools_used=tools_used, mode=mode
        )

    except Exception as e:
        logger.exception("Error in conversation workflow")
        return ConversationResponse(
            success=False, response=f"Error: {e!s}", tools_used=[], mode="error"
        )
    finally:
        await deps.cleanup()


__all__ = ["conversation_workflow"]
