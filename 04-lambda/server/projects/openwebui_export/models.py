"""Pydantic models for Open WebUI export API."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ConversationMessage(BaseModel):
    """Single message in a conversation."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ConversationExportRequest(BaseModel):
    """Request to export a conversation to RAG."""
    conversation_id: str = Field(..., description="Open WebUI conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[ConversationMessage] = Field(..., description="Conversation messages")
    topics: Optional[List[str]] = Field(None, description="Conversation topics")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ConversationExportResponse(BaseModel):
    """Response from conversation export."""
    success: bool
    conversation_id: str
    document_id: Optional[str] = None
    chunks_created: int = 0
    message: str
    errors: List[str] = []


class ConversationListRequest(BaseModel):
    """Request to list conversations from Open WebUI."""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of conversations to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


class ConversationListResponse(BaseModel):
    """Response with list of conversations."""
    conversations: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int

