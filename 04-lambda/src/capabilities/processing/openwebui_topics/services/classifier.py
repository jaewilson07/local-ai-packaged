"""Topic classification using LLM."""

import json
import logging

import httpx
from capabilities.processing.openwebui_topics.config import config
from capabilities.processing.openwebui_topics.models import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)

logger = logging.getLogger(__name__)


class TopicClassifier:
    """Classifies conversation topics using LLM."""

    def __init__(self):
        """Initialize the topic classifier."""
        self.llm_url = f"{config.llm_base_url}/chat/completions"
        self.model = config.llm_model

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format conversation messages into a single text."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.capitalize()}: {content}\n")
        return "\n".join(formatted)

    def _create_classification_prompt(
        self, conversation_text: str, title: str | None = None
    ) -> str:
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

    async def classify(self, request: TopicClassificationRequest) -> TopicClassificationResponse:
        """
        Classify topics for a conversation.

        Args:
            request: Topic classification request

        Returns:
            Topic classification response
        """
        try:
            # Format conversation
            conversation_text = self._format_conversation(request.messages)

            # Create prompt
            prompt = self._create_classification_prompt(conversation_text, request.title)

            # Call LLM
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": self.model,
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

                response = await client.post(
                    self.llm_url, json=payload, headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()

                # Extract response
                content = result["choices"][0]["message"]["content"]
                classification = json.loads(content)

                topics = classification.get("topics", [])
                reasoning = classification.get("reasoning", "")

                # Limit topics
                topics = topics[: config.max_topics]

                logger.info(
                    f"Classified topics for conversation {request.conversation_id}: {topics}"
                )

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
