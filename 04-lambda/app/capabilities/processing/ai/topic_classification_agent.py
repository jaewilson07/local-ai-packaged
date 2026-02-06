"""Topic classification agent for processing conversations."""

from app.capabilities.processing.ai.dependencies import ProcessingDeps
from app.capabilities.processing.schemas import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from app.core.llm import get_llm_model


class ProcessingState(BaseModel):
    """Minimal shared state for processing agents."""


# Create the topic classification agent
topic_classification_agent = Agent(
    get_llm_model(),
    deps_type=ProcessingDeps,
    system_prompt=(
        "You are an expert assistant for classifying conversation topics. "
        "You help users identify and organize conversation themes. "
        "Always provide clear, concise topic classifications. "
        "Respond with a JSON object containing 'topics' (array of 3-5 strings) "
        "and 'reasoning' (brief explanation)."
    ),
)


@topic_classification_agent.tool
async def classify_conversation_topics(
    ctx: RunContext[ProcessingDeps],
    conversation_id: str,
    messages: list[dict],
    title: str | None = None,
    existing_topics: list[str] | None = None,
) -> str:
    """
    Classify topics for a conversation.

    This tool analyzes a conversation and suggests 3-5 topics that best describe
    the conversation's main themes. Topics can be used for organization and filtering.

    Args:
        ctx: Agent runtime context with dependencies
        conversation_id: Conversation ID
        messages: Conversation messages
        title: Conversation title (optional)
        existing_topics: Existing topics to consider (optional)

    Returns:
        String describing the classified topics
    """
    from capabilities.processing.openwebui_topics.tools import classify_topics as _classify

    request = TopicClassificationRequest(
        conversation_id=conversation_id,
        title=title,
        messages=messages,
        existing_topics=existing_topics,
    )

    result: TopicClassificationResponse = await _classify(ctx, request)

    return (
        f"Classified topics for conversation {result.conversation_id}: {', '.join(result.topics)}. "
        f"Confidence: {result.confidence:.2f}. "
        f"Reasoning: {result.reasoning or 'N/A'}"
    )


__all__ = [
    "ProcessingState",
    "classify_conversation_topics",
    "topic_classification_agent",
]
