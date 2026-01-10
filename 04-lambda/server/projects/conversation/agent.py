"""Conversation orchestration agent."""

import logging
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pydantic_ai.ag_ui import StateDeps

from server.projects.shared.llm import get_llm_model
from server.projects.conversation.config import config
from server.projects.conversation.models import ConversationRequest, ConversationResponse
from server.projects.conversation.services.orchestrator import ConversationOrchestrator
from server.projects.persona.dependencies import PersonaDeps
from server.projects.persona.tools import get_voice_instructions, record_interaction

logger = logging.getLogger(__name__)


class ConversationState(BaseModel):
    """Minimal shared state for the Conversation agent."""
    pass


CONVERSATION_SYSTEM_PROMPT = """You are a conversation orchestrator that coordinates multiple AI agents and tools.

You can:
- Plan responses using available tools
- Coordinate memory, knowledge, and persona systems
- Generate natural, context-aware responses
- Record interactions for persona state updates
"""


conversation_agent = Agent(
    get_llm_model(),
    deps_type=StateDeps[ConversationState],
    system_prompt=CONVERSATION_SYSTEM_PROMPT
)


@conversation_agent.tool
async def orchestrate_conversation_tool(
    ctx: RunContext[StateDeps[ConversationState]],
    user_id: str = Field(..., description="User ID"),
    persona_id: str = Field(..., description="Persona ID"),
    message: str = Field(..., description="User message"),
) -> str:
    """
    Orchestrate a conversation by coordinating multiple agents and tools.
    
    This tool:
    1. Gets persona voice instructions
    2. Plans the response using available tools
    3. Executes tools if needed
    4. Generates final response
    5. Records interaction for persona state updates
    """
    import openai
    
    # Initialize dependencies
    persona_deps = PersonaDeps.from_settings()
    await persona_deps.initialize()
    
    try:
        # Get voice instructions
        voice_instructions = await get_voice_instructions(persona_deps, user_id, persona_id)
        
        # Create orchestrator
        orchestrator = ConversationOrchestrator(llm_client=persona_deps.openai_client)
        
        # Plan response
        available_tools = [
            "enhanced_search", "search_facts", "get_context_window",
            "create_calendar_event", "list_calendar_events"
        ]
        plan = await orchestrator.plan_response(message, voice_instructions, available_tools)
        
        # Execute tools (simplified - in production, would route to actual tool execution)
        tool_results = {}
        if plan.get("tools"):
            # For now, just note which tools would be used
            tool_results = {tool: f"Tool {tool} would be executed here" for tool in plan.get("tools", [])}
        
        # Generate response
        response = await orchestrator.generate_response(
            message, voice_instructions, tool_results, plan
        )
        
        # Record interaction (async, don't wait)
        try:
            await record_interaction(
                persona_deps, user_id, persona_id, message, response
            )
        except Exception as e:
            logger.warning(f"Error recording interaction: {e}")
        
        return response
    
    finally:
        await persona_deps.cleanup()
