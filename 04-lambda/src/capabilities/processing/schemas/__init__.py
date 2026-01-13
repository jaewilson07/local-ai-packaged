"""Processing capability schemas.

Pydantic models for topic classification and content processing.
"""

from pydantic import BaseModel, Field


class TopicClassificationRequest(BaseModel):
    """Request to classify conversation topics."""

    conversation_id: str = Field(..., description="Conversation ID")
    title: str | None = Field(None, description="Conversation title")
    messages: list[dict] = Field(..., description="Conversation messages")
    existing_topics: list[str] | None = Field(None, description="Existing topics to consider")


class TopicClassificationResponse(BaseModel):
    """Response with classified topics."""

    conversation_id: str
    topics: list[str]
    confidence: float
    reasoning: str | None = None


__all__ = [
    "TopicClassificationRequest",
    "TopicClassificationResponse",
]
