"""Action tool for tracking relationship level with users."""

from datetime import datetime
from typing import Any

import openai
from capabilities.persona.persona_state.config import config
from capabilities.persona.persona_state.models import RelationshipState
from capabilities.persona.persona_state.protocols import PersonaStore
from server.core.exceptions import LLMException


def calculate_relationship_update(
    current_relationship: RelationshipState | None,
    user_message: str,
    bot_response: str,
    llm_client: openai.AsyncOpenAI | None = None,
) -> RelationshipState:
    """
    Calculate relationship update based on interaction.

    Uses LLM to analyze sentiment and relationship dynamics.

    Args:
        current_relationship: Current relationship state (None for new)
        user_message: User's message
        bot_response: Bot's response
        llm_client: Optional OpenAI client

    Returns:
        Updated relationship state
    """
    # Start with defaults or current values
    affection = 0.0
    trust = 0.5
    interaction_count = 0

    if current_relationship:
        affection = current_relationship.affection_score
        trust = current_relationship.trust_level
        interaction_count = current_relationship.interaction_count

    if llm_client:
        # Use LLM for relationship analysis
        try:
            prompt = f"""Analyze the relationship dynamics in this conversation.

User message: {user_message}
Bot response: {bot_response}

Current relationship:
- Affection: {affection}
- Trust: {trust}
- Interactions: {interaction_count}

Determine relationship changes:
1. Affection change (-0.2 to +0.2)
2. Trust change (-0.1 to +0.1)

Respond in format: affection_change|trust_change
Example: 0.1|0.05"""

            response = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result = response.choices[0].message.content or "0.0|0.0"
            parts = result.split("|")
            affection_change = float(parts[0].strip()) if len(parts) > 0 else 0.0
            trust_change = float(parts[1].strip()) if len(parts) > 1 else 0.0

            affection = max(-1.0, min(1.0, affection + affection_change))
            trust = max(0.0, min(1.0, trust + trust_change))
        except (LLMException, ValueError, RuntimeError):
            # Fall back to simple analysis
            pass

    # Simplified relationship analysis (fallback)
    message_lower = (user_message + " " + bot_response).lower()

    # Positive indicators increase affection
    if any(word in message_lower for word in ["love", "appreciate", "thank", "great", "awesome"]):
        affection = min(1.0, affection + 0.1)
        trust = min(1.0, trust + 0.05)
    # Negative indicators decrease affection
    elif any(word in message_lower for word in ["hate", "disappointed", "angry", "frustrated"]):
        affection = max(-1.0, affection - 0.1)
        trust = max(0.0, trust - 0.05)
    # Neutral interactions slightly increase trust over time
    else:
        trust = min(1.0, trust + 0.02)

    interaction_count += 1

    return RelationshipState(
        user_id=current_relationship.user_id if current_relationship else "",
        persona_id=current_relationship.persona_id if current_relationship else "",
        affection_score=affection,
        trust_level=trust,
        interaction_count=interaction_count,
        last_interaction=datetime.now(),
    )


async def track_relationship_action(
    user_id: str,
    persona_id: str,
    user_message: str,
    bot_response: str,
    persona_store: PersonaStore,
    llm_client: openai.AsyncOpenAI | None = None,
) -> dict[str, Any]:
    """
    Track relationship level based on interaction.

    Args:
        user_id: User identifier
        persona_id: Persona identifier
        user_message: User's message
        bot_response: Bot's response
        persona_store: Persona store
        llm_client: Optional OpenAI client

    Returns:
        Dict with updated relationship state
    """
    current = persona_store.get_relationship(user_id, persona_id)

    # If no current relationship, create initial state
    if not current:
        current = RelationshipState(
            user_id=user_id,
            persona_id=persona_id,
            affection_score=0.0,
            trust_level=0.5,
            interaction_count=0,
            last_interaction=None,
        )

    updated = calculate_relationship_update(current, user_message, bot_response, llm_client)
    updated.user_id = user_id
    updated.persona_id = persona_id

    persona_store.update_relationship(user_id, persona_id, updated)

    return {"relationship": updated.model_dump()}
