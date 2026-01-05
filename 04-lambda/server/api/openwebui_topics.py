"""Open WebUI topic classification REST API endpoints."""

from fastapi import APIRouter, HTTPException
import logging

from server.projects.openwebui_topics.models import (
    TopicClassificationRequest,
    TopicClassificationResponse
)
from server.projects.openwebui_topics.classifier import TopicClassifier

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/classify", response_model=TopicClassificationResponse)
async def classify_topics(request: TopicClassificationRequest):
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
    classifier = TopicClassifier()
    try:
        result = await classifier.classify(request)
        return result
    except Exception as e:
        logger.exception(f"Failed to classify topics: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

