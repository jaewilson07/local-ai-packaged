"""Core capability functions for Open WebUI topic classification operations."""

import json
import logging

from capabilities.processing.openwebui_topics.dependencies import OpenWebUITopicsDeps
from capabilities.processing.openwebui_topics.models import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)
from pydantic_ai import RunContext

logger = logging.getLogger(__name__)


def _format_conversation(messages: list[dict]) -> str:
    """Format conversation messages into a single text."""
    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role.capitalize()}: {content}\n")
    return "\n".join(formatted)


def _create_classification_prompt(conversation_text: str, title: str | None = None) -> str:
    """Create prompt for topic classification."""
    title_part = f"\nTitle: {title}\n" if title else ""
    return f"""Analyze the following conversation and identify 3-5 main topics.
Topics should be concise (1-3 words each) and descriptive of the conversation's main themes.

{title_part}Conversation:
{conversation_text}

Respond with a JSON object containing:
- "topics": array of topic strings (3-5 topics)
- "reasoning": brief explanation of why these topics were chosen

Example response:
{{
  "topics": ["authentication", "API setup", "security"],
  "reasoning": "The conversation discusses setting up authentication for an API with security considerations"
}}"""


async def classify_topics(
    ctx: RunContext[OpenWebUITopicsDeps], request: TopicClassificationRequest
) -> TopicClassificationResponse:
    """
    Classify topics for a conversation using LLM.

    Args:
        ctx: Agent runtime context with dependencies
        request: Topic classification request

    Returns:
        Topic classification response
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()

    try:
        # Format conversation
        conversation_text = _format_conversation(request.messages)

        # Create prompt
        prompt = _create_classification_prompt(conversation_text, request.title)

        # Call LLM
        payload = {
            "model": deps.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a topic classification assistant. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        response = await deps.http_client.post(deps.llm_url, json=payload)
        response.raise_for_status()
        result = response.json()

        # Extract response
        content = result["choices"][0]["message"]["content"]
        classification = json.loads(content)

        topics = classification.get("topics", [])
        reasoning = classification.get("reasoning", "")

        # Limit topics
        topics = topics[: deps.max_topics]

        logger.info(f"Classified topics for conversation {request.conversation_id}: {topics}")

        return TopicClassificationResponse(
            conversation_id=request.conversation_id,
            topics=topics,
            confidence=0.8,  # Default confidence
            reasoning=reasoning,
        )

    except Exception as e:
        logger.exception(
            f"Failed to classify topics for conversation {request.conversation_id}: {e}"
        )
        # Return default topics on error
        return TopicClassificationResponse(
            conversation_id=request.conversation_id,
            topics=["general"],
            confidence=0.0,
            reasoning=f"Classification failed: {e!s}",
        )
