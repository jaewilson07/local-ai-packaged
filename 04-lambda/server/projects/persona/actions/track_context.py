"""Action tool for tracking conversation context and mode."""

from typing import Any

import openai

from server.projects.persona.config import config
from server.projects.persona.models import ConversationContext
from server.projects.persona.protocols import PersonaStore


def analyze_conversation_context(
    user_message: str, bot_response: str, llm_client: openai.AsyncOpenAI | None = None
) -> ConversationContext:
    """
    Analyze conversation context and determine mode.

    Uses LLM to analyze conversation depth, topic, and emotional tone.

    Args:
        user_message: User's message
        bot_response: Bot's response
        llm_client: Optional OpenAI client

    Returns:
        Conversation context
    """
    if llm_client:
        try:
            prompt = f"""Analyze this conversation and determine the conversation mode and topic.

User message: {user_message}
Bot response: {bot_response}

Determine:
1. Conversation mode (deep_empathy, casual_chat, storytelling, balanced_factual, balanced)
2. Topic (if identifiable, otherwise null)
3. Depth level (1-5, where 1 is surface level and 5 is very deep)

Respond in format: mode|topic|depth
Example: deep_empathy|relationships|4"""

            response = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result = response.choices[0].message.content or "balanced||3"
            parts = result.split("|")
            mode = parts[0].strip() if len(parts) > 0 else "balanced"
            topic = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            depth = int(parts[2].strip()) if len(parts) > 2 else 3
            depth = max(1, min(5, depth))  # Clamp to 1-5

            return ConversationContext(
                mode=mode,
                topic=topic,
                depth_level=depth,
            )
        except Exception:
            # Fall back to simple analysis
            pass

    # Simplified context analysis (fallback)
    message_lower = (user_message + " " + bot_response).lower()

    # Determine conversation mode
    if any(
        word in message_lower for word in ["feel", "emotion", "sad", "happy", "anxious", "worried"]
    ):
        mode = "deep_empathy"
        depth = 4
    elif any(word in message_lower for word in ["story", "remember", "happened", "experience"]):
        mode = "storytelling"
        depth = 4
    elif any(word in message_lower for word in ["what", "how", "why", "explain", "tell me"]):
        mode = "balanced_factual"
        depth = 3
    elif any(word in message_lower for word in ["hey", "hi", "hello", "how are you", "what's up"]):
        mode = "casual_chat"
        depth = 2
    else:
        mode = "balanced"
        depth = 3

    # Extract topic (simplified)
    topic = None
    topic_keywords = {
        "technology": ["tech", "code", "programming", "computer"],
        "relationships": ["friend", "partner", "family", "love"],
        "work": ["job", "work", "career", "office"],
        "hobbies": ["hobby", "interest", "fun", "activity"],
    }

    for topic_name, keywords in topic_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            topic = topic_name
            break

    return ConversationContext(
        mode=mode,
        topic=topic,
        depth_level=depth,
    )


async def track_context_action(
    user_id: str,
    persona_id: str,
    user_message: str,
    bot_response: str,
    persona_store: PersonaStore,
    llm_client: openai.AsyncOpenAI | None = None,
) -> dict[str, Any]:
    """
    Track conversation context based on interaction.

    Args:
        user_id: User identifier
        persona_id: Persona identifier
        user_message: User's message
        bot_response: Bot's response
        persona_store: Persona store
        llm_client: Optional OpenAI client

    Returns:
        Dict with updated conversation context
    """
    context = analyze_conversation_context(user_message, bot_response, llm_client)
    persona_store.update_conversation_context(user_id, persona_id, context)

    return {"context": context.model_dump()}
