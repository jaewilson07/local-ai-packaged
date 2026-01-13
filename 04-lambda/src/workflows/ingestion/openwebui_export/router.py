"""Open WebUI export REST API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import RunContext
from src.shared.dependency_factory import create_dependency_factory
from src.workflows.ingestion.openwebui_export.dependencies import OpenWebUIExportDeps
from src.workflows.ingestion.openwebui_export.models import (
    ConversationExportRequest,
    ConversationExportResponse,
    ConversationListResponse,
)
from src.workflows.ingestion.openwebui_export.tools import (
    export_conversation,
    export_conversations_batch,
    get_conversation,
    get_conversations,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Use dependency factory to create deps getter (eliminates boilerplate)
get_openwebui_export_deps = create_dependency_factory(OpenWebUIExportDeps)


@router.post("/export", response_model=ConversationExportResponse)
async def export_conversation_endpoint(
    request: ConversationExportRequest,
    deps: Annotated[OpenWebUIExportDeps, Depends(get_openwebui_export_deps)],
):
    """
    Export a conversation from Open WebUI to MongoDB RAG system.

    This endpoint takes a conversation (messages, metadata, topics) and exports it
    to the MongoDB RAG system where it becomes searchable via vector search.

    **Use Cases:**
    - Export conversations for RAG searchability
    - Make conversation history searchable
    - Integrate conversations with knowledge base

    **Request Body:**
    ```json
    {
        "conversation_id": "conv_123",
        "user_id": "user_456",
        "title": "Discussion about authentication",
        "messages": [
            {"role": "user", "content": "How do I set up auth?"},
            {"role": "assistant", "content": "To set up authentication..."}
        ],
        "topics": ["authentication", "setup"],
        "metadata": {"custom_field": "value"}
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "conversation_id": "conv_123",
        "document_id": "507f1f77bcf86cd799439011",
        "chunks_created": 5,
        "message": "Conversation exported successfully",
        "errors": []
    }
    ```
    """
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await export_conversation(tool_ctx, request)
        return ConversationExportResponse(**result)
    except Exception as e:
        logger.exception("Failed to export conversation")
        raise HTTPException(status_code=500, detail=f"Export failed: {e!s}") from e


@router.post("/export/batch", response_model=list[ConversationExportResponse])
async def export_conversations_batch_endpoint(
    requests: list[ConversationExportRequest],
    deps: Annotated[OpenWebUIExportDeps, Depends(get_openwebui_export_deps)],
):
    """
    Export multiple conversations in batch.

    This endpoint exports multiple conversations at once, which is more efficient
    than calling the single export endpoint multiple times.
    """
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        results = await export_conversations_batch(tool_ctx, requests)
        return [ConversationExportResponse(**result) for result in results]
    except Exception as e:
        logger.exception("Batch export failed")
        raise HTTPException(status_code=500, detail=f"Batch export failed: {e!s}") from e


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations_endpoint(
    deps: Annotated[OpenWebUIExportDeps, Depends(get_openwebui_export_deps)],
    user_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List conversations from Open WebUI.

    This endpoint fetches conversations from Open WebUI API. Useful for
    discovering conversations that need to be exported.
    """
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await get_conversations(tool_ctx, user_id, limit, offset)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return ConversationListResponse(
            conversations=result["conversations"],
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list conversations")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {e!s}") from e


@router.get("/conversations/{conversation_id}")
async def get_conversation_endpoint(
    conversation_id: str, deps: Annotated[OpenWebUIExportDeps, Depends(get_openwebui_export_deps)]
):
    """
    Get a specific conversation from Open WebUI.

    This endpoint fetches a single conversation by ID from Open WebUI API.
    """
    try:
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await get_conversation(tool_ctx, conversation_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get conversation {conversation_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {e!s}") from e
