"""Action tool for tracking persona mood based on interactions."""

from datetime import datetime
from typing import Any

import openai
from app.capabilities.persona.persona_state.config import config
from app.capabilities.persona.persona_state.models import MoodState
from app.capabilities.persona.persona_state.protocols import PersonaStore
from app.core.exceptions import LLMException


def analyze_mood_from_interaction(
    user_message: str,
    bot_response: str,
    persona_store: PersonaStore,
    user_id: str,
    persona_id: str,
    llm_client: openai.AsyncOpenAI | None = None,
) -> MoodState:
    """
    Analyze mood from interaction and return updated mood state.

    Uses LLM to analyze emotional tone and determine mood changes.

    Args:
        user_message: User's message
        bot_response: Bot's response
        persona_store: Persona store for retrieving current mood
        user_id: User ID
        persona_id: Persona ID
        llm_client: Optional OpenAI client

    Returns:
        Updated mood state
    """
    # Get current mood
    current_mood = persona_store.get_mood(user_id, persona_id)

    if llm_client:
        # Use LLM for mood analysis
        try:
            prompt = f"""Analyze the emotional tone of this conversation and determine the persona's mood.

User message: {user_message}
Bot response: {bot_response}

Current mood: {current_mood.primary_emotion if current_mood else "neutral"} (intensity: {current_mood.intensity if current_mood else 0.5})

Determine:
1. Primary emotion (happy, sad, excited, neutral, angry, anxious, etc.)
2. Intensity (0.0 to 1.0)

Respond in format: emotion|intensity
Example: happy|0.7"""

            response = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result = response.choices[0].message.content or "neutral|0.5"
            parts = result.split("|")
            emotion = parts[0].strip().lower() if len(parts) > 0 else "neutral"
            intensity = float(parts[1].strip()) if len(parts) > 1 else 0.5
            intensity = max(0.0, min(1.0, intensity))  # Clamp to 0-1

            return MoodState(
                primary_emotion=emotion,
                intensity=intensity,
                timestamp=datetime.now(),
            )
        except (LLMException, ValueError, RuntimeError):
            # Fall back to simple analysis
            pass

    # Simplified mood analysis (fallback)
    message_lower = (user_message + " " + bot_response).lower()

    if any(word in message_lower for word in ["happy", "excited", "great", "awesome", "love"]):
        emotion = "happy"
        intensity = 0.7
    elif any(word in message_lower for word in ["sad", "upset", "disappointed", "sorry"]):
        emotion = "sad"
        intensity = 0.6
    elif any(word in message_lower for word in ["angry", "frustrated", "annoyed", "mad"]):
        emotion = "angry"
        intensity = 0.7
    elif any(word in message_lower for word in ["excited", "thrilled", "amazing", "wow"]):
        emotion = "excited"
        intensity = 0.8
    else:
        emotion = current_mood.primary_emotion if current_mood else "neutral"
        intensity = current_mood.intensity if current_mood else 0.5

    return MoodState(
        primary_emotion=emotion,
        intensity=intensity,
        timestamp=datetime.now(),
    )


async def track_mood_action(
    user_id: str,
    persona_id: str,
    user_message: str,
    bot_response: str,
    persona_store: PersonaStore,
    llm_client: openai.AsyncOpenAI | None = None,
) -> dict[str, Any]:
    """
    Track mood based on interaction.

    Args:
        user_id: User identifier
        persona_id: Persona identifier
        user_message: User's message
        bot_response: Bot's response
        persona_store: Persona store
        llm_client: Optional OpenAI client for LLM-based analysis

    Returns:
        Dict with updated mood state
    """
    mood = analyze_mood_from_interaction(
        user_message, bot_response, persona_store, user_id, persona_id, llm_client
    )
    persona_store.update_mood(user_id, persona_id, mood)

    return {"mood": mood.model_dump()}
