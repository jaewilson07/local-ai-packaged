"""Conversation orchestration REST API."""

import logging
from typing import Annotated

from capabilities.persona.ai.dependencies import PersonaDeps
from capabilities.persona.ai.tools import get_voice_instructions
from fastapi import APIRouter, Depends, HTTPException
from workflows.chat.conversation.schemas import ConversationRequest, ConversationResponse
from workflows.chat.conversation.services.orchestrator import ConversationOrchestrator

from shared.dependency_factory import create_dependency_factory

router = APIRouter(prefix="/api/v1/conversation", tags=["workflows", "conversation"])
logger = logging.getLogger(__name__)

# Use dependency factory to create deps getter (eliminates boilerplate)
get_persona_deps = create_dependency_factory(PersonaDeps)


@router.post("/orchestrate", response_model=ConversationResponse)
async def orchestrate_conversation_endpoint(
    request: ConversationRequest, deps: Annotated[PersonaDeps, Depends(get_persona_deps)]
):
    """
    Orchestrate a conversation by coordinating multiple agents and tools.

    This endpoint:
    1. Gets persona voice instructions
    2. Plans the response using available tools
    3. Executes tools if needed
    4. Generates final response
    5. Records interaction for persona state updates
    """
    try:
        # Get voice instructions
        voice_instructions = await get_voice_instructions(deps, request.user_id, request.persona_id)

        # Create orchestrator
        orchestrator = ConversationOrchestrator(llm_client=deps.openai_client)

        # Plan response
        available_tools = [
            "enhanced_search",
            "search_facts",
            "get_context_window",
            "create_calendar_event",
            "list_calendar_events",
        ]
        plan = await orchestrator.plan_response(
            request.message, voice_instructions, available_tools
        )

        # Execute tools (simplified - in production, would route to actual tool execution)
        tool_results = {}
        tools_used = []
        if plan.get("tools"):
            # For now, just note which tools would be used
            tools_used = plan.get("tools", [])
            tool_results = {tool: f"Tool {tool} would be executed here" for tool in tools_used}

        # Generate response
        response = await orchestrator.generate_response(
            request.message, voice_instructions, tool_results, plan
        )

        # Record interaction (async, don't wait)
        try:
            from capabilities.persona.persona_state.tools import record_interaction

            await record_interaction(
                deps, request.user_id, request.persona_id, request.message, response
            )
        except Exception as e:
            logger.warning(f"Error recording interaction: {e}")

        return ConversationResponse(
            success=True,
            response=response,
            tools_used=tools_used,
            mode=plan.get("action", "balanced"),
        )

    except Exception as e:
        logger.exception("Error orchestrating conversation")
        raise HTTPException(status_code=500, detail=str(e)) from e
