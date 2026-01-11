"""Main Open WebUI Topics agent implementation."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional, List
from pydantic_ai.ag_ui import StateDeps

from server.projects.shared.llm import get_llm_model as _get_openwebui_topics_model
from server.projects.openwebui_topics.config import config
from server.projects.openwebui_topics.dependencies import OpenWebUITopicsDeps
from server.projects.openwebui_topics.models import TopicClassificationRequest
from server.projects.openwebui_topics.tools import classify_topics


class OpenWebUITopicsState(BaseModel):
    """Minimal shared state for the Open WebUI topics agent."""
    pass


# Create the Open WebUI topics agent with OpenWebUITopicsDeps
# Changed from StateDeps[OpenWebUITopicsState] to OpenWebUITopicsDeps to match tool requirements
openwebui_topics_agent = Agent(
    _get_openwebui_topics_model(),
    deps_type=OpenWebUITopicsDeps,
    system_prompt=(
        "You are an expert assistant for classifying conversation topics. "
        "You help users identify and organize conversation themes. "
        "Always provide clear, concise topic classifications."
    )
)


# Register tools - create wrapper functions that bridge StateDeps to OpenWebUITopicsDeps
@openwebui_topics_agent.tool
async def classify_topics_tool(
    ctx: RunContext[OpenWebUITopicsDeps],
    conversation_id: str,
    messages: List[dict],
    title: Optional[str] = None,
    existing_topics: Optional[List[str]] = None
) -> str:
    """
    Classify topics for a conversation using LLM.
    
    This tool analyzes a conversation and suggests 3-5 topics that best describe
    the conversation's main themes. Topics can be used for organization and filtering.
    
    Args:
        ctx: Agent runtime context with state dependencies
        conversation_id: Conversation ID
        messages: Conversation messages
        title: Conversation title (optional)
        existing_topics: Existing topics to consider (optional)
    
    Returns:
        String describing the classified topics
    """
    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    
    request = TopicClassificationRequest(
        conversation_id=conversation_id,
        title=title,
        messages=messages,
        existing_topics=existing_topics
    )
    
    # Create RunContext for tools.py
    tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
    result = await classify_topics(tool_ctx, request)
    
    return (
        f"Classified topics for conversation {result.conversation_id}: {result.topics}. "
        f"Confidence: {result.confidence}. "
        f"Reasoning: {result.reasoning or 'N/A'}"
    )
