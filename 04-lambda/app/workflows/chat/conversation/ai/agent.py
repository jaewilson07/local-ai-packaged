"""Conversation orchestration agent."""

from pydantic import BaseModel
from pydantic_ai import Agent
from app.workflows.chat.conversation.ai.dependencies import ConversationDeps
from app.workflows.chat.conversation.tools import orchestrate_conversation

from app.core.llm import get_llm_model

CONVERSATION_SYSTEM_PROMPT = """You are a conversation orchestrator that coordinates multiple AI agents and tools.

You can:
- Plan responses using available tools
- Coordinate memory, knowledge, and persona systems
- Generate natural, context-aware responses
- Record interactions for persona state updates
"""


class ConversationState(BaseModel):
    """Minimal shared state for the Conversation agent."""


conversation_agent = Agent(
    get_llm_model(), deps_type=ConversationDeps, system_prompt=CONVERSATION_SYSTEM_PROMPT
)


@conversation_agent.tool
async def orchestrate_conversation_tool(
    ctx,
    user_id: str,
    persona_id: str,
    message: str,
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
    return await orchestrate_conversation(
        ctx, user_id=user_id, persona_id=persona_id, message=message
    )


__all__ = ["CONVERSATION_SYSTEM_PROMPT", "ConversationState", "conversation_agent"]
