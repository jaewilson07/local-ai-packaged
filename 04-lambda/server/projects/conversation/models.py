"""Pydantic models for conversation orchestration."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ConversationRequest(BaseModel):
    """Request for conversation orchestration."""
    user_id: str = Field(..., description="User ID")
    persona_id: str = Field(..., description="Persona ID")
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ConversationResponse(BaseModel):
    """Response from conversation orchestration."""
    success: bool = Field(..., description="Whether the operation was successful")
    response: str = Field(..., description="Bot response")
    tools_used: List[str] = Field(default_factory=list, description="Tools used in response")
    mode: str = Field(default="balanced", description="Conversation mode used")
