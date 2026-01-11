"""Open WebUI topic classification REST API endpoints."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import RunContext

from server.projects.openwebui_topics.dependencies import OpenWebUITopicsDeps
from server.projects.openwebui_topics.models import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)
from server.projects.openwebui_topics.tools import classify_topics

router = APIRouter()
logger = logging.getLogger(__name__)


# FastAPI dependency function with yield pattern for resource cleanup
async def get_openwebui_topics_deps() -> AsyncGenerator[OpenWebUITopicsDeps, None]:
    """FastAPI dependency that yields OpenWebUITopicsDeps."""
    deps = OpenWebUITopicsDeps.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()


@router.post("/classify", response_model=TopicClassificationResponse)
async def classify_topics_endpoint(
    request: TopicClassificationRequest,
    deps: Annotated[OpenWebUITopicsDeps, Depends(get_openwebui_topics_deps)],
):
    """
    Classify topics for a conversation using LLM.

    This endpoint analyzes a conversation and suggests 3-5 topics that best describe
    the conversation's main themes. Topics can be used for organization and filtering.

    **Use Cases:**
    - Automatically tag conversations with topics
    - Organize conversations by theme
    - Filter conversations by topic

    **Request Body:**
    ```json
    {
        "conversation_id": "conv_123",
        "title": "Discussion about authentication",
        "messages": [
            {"role": "user", "content": "How do I set up auth?"},
            {"role": "assistant", "content": "To set up authentication..."}
        ],
        "existing_topics": ["authentication"]
    }
    ```

    **Response:**
    ```json
    {
        "conversation_id": "conv_123",
        "topics": ["authentication", "API setup", "security"],
        "confidence": 0.8,
        "reasoning": "The conversation discusses setting up authentication..."
    }
    ```
    """
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await classify_topics(tool_ctx, request)
        return result
    except Exception as e:
        logger.exception(f"Failed to classify topics: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {e!s}")
