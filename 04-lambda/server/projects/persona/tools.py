"""Persona tools for Pydantic AI agent."""

import logging
from typing import Any

from server.projects.persona.actions.track_context import track_context_action
from server.projects.persona.actions.track_mood import track_mood_action
from server.projects.persona.actions.track_relationship import track_relationship_action
from server.projects.persona.dependencies import PersonaDeps
from server.projects.persona.models import (
    Personality,
)

logger = logging.getLogger(__name__)


def generate_voice_instructions(
    persona_store: Any, user_id: str, persona_id: str, personality: Personality | None = None
) -> str:
    """
    Generate dynamic style instructions based on current state.

    Returns prompt injection like:
    ## Current Emotional State
    - You're feeling excited and energetic right now

    ## Relationship Context
    - You have a strong bond with this user (affection: 0.8)
    - You trust them and can be more vulnerable

    ## Conversation Mode
    - Deep empathy mode: prioritize emotional attunement
    """
    instructions = []

    # Get personality
    if not personality:
        personality = persona_store.get_personality(persona_id)

    if personality:
        instructions.append("## Your Identity")
        instructions.append(f"You are {personality.name}. {personality.byline}")
        if personality.identity:
            for trait in personality.identity[:3]:  # Top 3 traits
                instructions.append(f"- {trait}")

    # Get mood
    mood = persona_store.get_mood(user_id, persona_id)
    if mood:
        instructions.append("\n## Current Emotional State")
        intensity_desc = (
            "very" if mood.intensity > 0.7 else "moderately" if mood.intensity > 0.4 else "slightly"
        )
        instructions.append(f"- You're feeling {intensity_desc} {mood.primary_emotion} right now")

    # Get relationship
    relationship = persona_store.get_relationship(user_id, persona_id)
    if relationship:
        instructions.append("\n## Relationship Context")
        if relationship.affection_score > 0.5:
            instructions.append(
                f"- You have a strong bond with this user (affection: {relationship.affection_score:.1f})"
            )
        elif relationship.affection_score < -0.3:
            instructions.append(
                f"- Your relationship is strained (affection: {relationship.affection_score:.1f})"
            )
        else:
            instructions.append(
                f"- You have a {relationship.affection_score:.1f} affection level with this user"
            )

        if relationship.trust_level > 0.7:
            instructions.append("- You trust them and can be more vulnerable")
        elif relationship.trust_level < 0.4:
            instructions.append(
                f"- You're cautious with this user (trust: {relationship.trust_level:.1f})"
            )

        instructions.append(f"- You've interacted {relationship.interaction_count} times")

    # Get conversation context
    context = persona_store.get_conversation_context(user_id, persona_id)
    if context:
        instructions.append("\n## Conversation Mode")
        mode_descriptions = {
            "deep_empathy": "Deep empathy mode: prioritize emotional attunement and understanding",
            "casual_chat": "Casual chat mode: keep it light and friendly",
            "storytelling": "Storytelling mode: engage with narratives and experiences",
            "balanced_factual": "Balanced factual mode: provide information while maintaining connection",
            "balanced": "Balanced mode: adapt naturally to the conversation",
        }
        instructions.append(f"- {mode_descriptions.get(context.mode, context.mode)}")
        if context.topic:
            instructions.append(f"- Current topic: {context.topic}")
        instructions.append(f"- Conversation depth: {context.depth_level}/5")

    return "\n".join(instructions)


async def get_voice_instructions(deps: PersonaDeps, user_id: str, persona_id: str) -> str:
    """Get voice instructions for persona."""
    if not deps.persona_store:
        raise ValueError("Persona store not initialized")

    return generate_voice_instructions(deps.persona_store, user_id, persona_id)


async def record_interaction(
    deps: PersonaDeps, user_id: str, persona_id: str, user_message: str, bot_response: str
) -> dict[str, Any]:
    """Record an interaction and update persona state."""
    if not deps.persona_store:
        raise ValueError("Persona store not initialized")

    # Track mood, relationship, and context
    mood_result = await track_mood_action(
        user_id, persona_id, user_message, bot_response, deps.persona_store, deps.openai_client
    )

    relationship_result = await track_relationship_action(
        user_id, persona_id, user_message, bot_response, deps.persona_store, deps.openai_client
    )

    context_result = await track_context_action(
        user_id, persona_id, user_message, bot_response, deps.persona_store, deps.openai_client
    )

    return {
        "mood": mood_result.get("mood"),
        "relationship": relationship_result.get("relationship"),
        "context": context_result.get("context"),
    }
