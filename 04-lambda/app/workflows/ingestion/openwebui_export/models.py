"""Models for OpenWebUI export operations."""

from typing import Any

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str | None = Field(None, description="Message timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationExportRequest(BaseModel):
    """Request to export a conversation."""

    conversation_id: str = Field(..., description="Conversation ID to export")
    include_metadata: bool = Field(True, description="Include metadata in export")


class ConversationExportResponse(BaseModel):
    """Response containing exported conversation."""

    conversation_id: str
    title: str | None = None
    messages: list[ConversationMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class ConversationListRequest(BaseModel):
    """Request to list conversations."""

    limit: int = Field(100, description="Maximum conversations to return")
    offset: int = Field(0, description="Pagination offset")


class ConversationListResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    success: bool = True


__all__ = [
    "ConversationExportRequest",
    "ConversationExportResponse",
    "ConversationListRequest",
    "ConversationListResponse",
    "ConversationMessage",
]
