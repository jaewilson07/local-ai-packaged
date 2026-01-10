"""Open WebUI export REST API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from pydantic_ai import RunContext

from server.core.api_utils import with_dependencies
from server.projects.openwebui_export.models import (
    ConversationExportRequest,
    ConversationExportResponse,
    ConversationListRequest,
    ConversationListResponse
)
from server.projects.openwebui_export.dependencies import OpenWebUIExportDeps
from server.projects.openwebui_export.tools import (
    export_conversation,
    get_conversations,
    get_conversation,
    export_conversations_batch
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/export", response_model=ConversationExportResponse)
@with_dependencies(OpenWebUIExportDeps)
async def export_conversation_endpoint(request: ConversationExportRequest, deps: OpenWebUIExportDeps):
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
        logger.exception(f"Failed to export conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/export/batch", response_model=List[ConversationExportResponse])
@with_dependencies(OpenWebUIExportDeps)
async def export_conversations_batch_endpoint(requests: List[ConversationExportRequest], deps: OpenWebUIExportDeps):
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
        logger.exception(f"Batch export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
@with_dependencies(OpenWebUIExportDeps)
async def list_conversations_endpoint(
    deps: OpenWebUIExportDeps,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
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
            offset=result["offset"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}")
@with_dependencies(OpenWebUIExportDeps)
async def get_conversation_endpoint(conversation_id: str, deps: OpenWebUIExportDeps):
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
        logger.exception(f"Failed to get conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

