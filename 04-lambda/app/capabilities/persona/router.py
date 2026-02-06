"""Persona capability REST API endpoints."""

import logging
from typing import Annotated

from app.capabilities.persona.ai import PersonaDeps
from app.capabilities.persona.persona_workflow import (
    character_chat_workflow,
    update_persona_mood_workflow,
)
from app.capabilities.persona.schemas import ChatRequest, ChatResponse
from fastapi import APIRouter, Depends, HTTPException

from shared.dependency_factory import create_dependency_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities", "persona"])

# Use dependency factory to create deps getter (eliminates boilerplate)
get_persona_deps = create_dependency_factory(PersonaDeps)


@router.post("/persona/chat", response_model=ChatResponse)
async def character_chat_endpoint(
    request: ChatRequest,
    deps: Annotated[PersonaDeps, Depends(get_persona_deps)],
) -> ChatResponse:
    """
    Generate a character response in Discord conversation.

    This endpoint orchestrates the full character interaction flow,
    including state retrieval, mood/relationship evaluation, and
    response generation.

    **Request Body:**
    ```json
    {
        "channel_id": "123456789",
        "character_id": "alice",
        "user_id": "987654321",
        "message": "Hello! How are you?",
        "message_id": "msg_123"
    }
    ```

    **Response:**
    ```json
    {
        "message": "Hi! I'm doing great, thanks for asking!",
        "mood": "happy",
        "relationship_feeling": "positive"
    }
    ```
    """
    try:
        result = await character_chat_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to generate character response")
        raise HTTPException(status_code=500, detail=f"Response generation failed: {e!s}") from e


@router.post("/persona/mood")
async def update_mood_endpoint(
    persona_id: str,
    new_mood: str,
    confidence: float = 0.5,
    deps: Annotated[PersonaDeps, Depends(get_persona_deps)] = None,
) -> dict[str, str]:
    """
    Update a persona's mood.

    This endpoint updates the current mood and mood confidence for a persona,
    affecting how they interact in subsequent conversations.

    **Query Parameters:**
    - `persona_id`: Unique persona identifier
    - `new_mood`: New mood state (happy, sad, excited, confused, neutral, etc.)
    - `confidence`: Confidence in the mood (0.0-1.0, default: 0.5)

    **Response:**
    ```json
    {
        "status": "success",
        "message": "Updated alice's mood to 'happy'"
    }
    ```
    """
    try:
        result = await update_persona_mood_workflow(persona_id, new_mood, confidence, deps)
        return result
    except Exception as e:
        logger.exception("Failed to update persona mood")
        raise HTTPException(status_code=500, detail=f"Mood update failed: {e!s}") from e


__all__ = [
    "get_persona_deps",
    "router",
]
