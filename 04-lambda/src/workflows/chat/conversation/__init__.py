"""Conversation orchestration workflow for coordinating multiple agents.

This module provides conversation orchestration capabilities organized by:
- schemas/: Request/Response models
- ai/: Agent definitions and dependencies
- workflow.py: High-level orchestration functions
- router.py: FastAPI endpoints
- tools.py: Core capability functions
"""

from workflows.chat.conversation.ai import (
    CONVERSATION_SYSTEM_PROMPT,
    ConversationDeps,
    ConversationState,
    conversation_agent,
)
from workflows.chat.conversation.schemas import ConversationRequest, ConversationResponse
from workflows.chat.conversation.workflow import conversation_workflow

__all__ = [
    # Schemas
    "ConversationRequest",
    "ConversationResponse",
    # AI Components
    "conversation_agent",
    "ConversationState",
    "CONVERSATION_SYSTEM_PROMPT",
    "ConversationDeps",
    # Workflows
    "conversation_workflow",
]
