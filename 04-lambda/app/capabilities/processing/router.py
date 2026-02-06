"""Processing capability REST API endpoints."""

import logging
from typing import Annotated

from app.capabilities.processing.ai import ProcessingDeps
from app.capabilities.processing.processing_workflow import classify_topics_workflow
from app.capabilities.processing.schemas import (
    TopicClassificationRequest,
    TopicClassificationResponse,
)
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependency_factory import create_dependency_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities", "processing"])

# Use dependency factory to create deps getter (eliminates boilerplate)
get_processing_deps = create_dependency_factory(ProcessingDeps)


@router.post("/processing/classify-topics", response_model=TopicClassificationResponse)
async def classify_topics_endpoint(
    request: TopicClassificationRequest,
    deps: Annotated[ProcessingDeps, Depends(get_processing_deps)],
) -> TopicClassificationResponse:
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
        result = await classify_topics_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to classify topics")
        raise HTTPException(status_code=500, detail=f"Classification failed: {e!s}") from e


__all__ = [
    "get_processing_deps",
    "router",
]
