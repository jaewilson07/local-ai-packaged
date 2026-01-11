"""Pydantic models for conversation orchestration."""

from typing import Any

from pydantic import BaseModel, Field


class ConversationRequest(BaseModel):
    """Request for conversation orchestration."""

    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    message: str = Field(..., description="User message")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ConversationResponse(BaseModel):
    """Response from conversation orchestration."""

    success: bool = Field(..., description="Whether the operation was successful")
    response: str = Field(..., description="Bot response")
    tools_used: list[str] = Field(default_factory=list, description="Tools used in response")
    mode: str = Field(default="balanced", description="Conversation mode used")
