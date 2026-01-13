"""Core capability functions for Conversation project."""

import logging

from capabilities.persona.persona_state.tools import get_voice_instructions, record_interaction
from pydantic import Field
from pydantic_ai import RunContext
from workflows.chat.conversation.ai.dependencies import ConversationDeps
from workflows.chat.conversation.services.orchestrator import ConversationOrchestrator

logger = logging.getLogger(__name__)


async def orchestrate_conversation(
    ctx: RunContext[ConversationDeps],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    message: str = Field(..., description="User message"),
) -> str:
    """
    Orchestrate a conversation by coordinating multiple agents and tools.

    This function:
    1. Gets persona voice instructions
    2. Plans the response using available tools
    3. Executes tools if needed
    4. Generates final response
    5. Records interaction for persona state updates

    Args:
        ctx: Runtime context with dependencies
        user_id: User ID
        persona_id: Persona ID
        message: User message

    Returns:
        Orchestrated response string
    """
    # Access dependencies from context - they are already initialized
    persona_deps = ctx.deps

    # Get voice instructions
    voice_instructions = await get_voice_instructions(persona_deps, user_id, persona_id)

    # Create orchestrator
    orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)

    # Plan response
    available_tools = [
        "enhanced_search",
        "search_facts",
        "get_context_window",
        "create_calendar_event",
        "list_calendar_events",
    ]
    plan = await orchestrator.plan_response(message, voice_instructions, available_tools)

    # Execute tools (simplified - in production, would route to actual tool execution)
    tool_results = {}
    if plan.get("tools"):
        # For now, just note which tools would be used
        tool_results = {
            tool: f"Tool {tool} would be executed here" for tool in plan.get("tools", [])
        }

    # Generate response
    response = await orchestrator.generate_response(message, voice_instructions, tool_results, plan)

    # Record interaction (async, don't wait)
    try:
        await record_interaction(persona_deps, user_id, persona_id, message, response)
    except Exception as e:
        logger.warning(f"Error recording interaction: {e}")

    return response
