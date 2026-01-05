"""Pydantic models for topic classification."""

from pydantic import BaseModel, Field
from typing import List, Optional


class TopicClassificationRequest(BaseModel):
    """Request to classify conversation topics."""
    conversation_id: str = Field(..., description="Conversation ID")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[dict] = Field(..., description="Conversation messages")
    existing_topics: Optional[List[str]] = Field(None, description="Existing topics to consider")


class TopicClassificationResponse(BaseModel):
    """Response with classified topics."""
    conversation_id: str
    topics: List[str]
    confidence: float
    reasoning: Optional[str] = None

