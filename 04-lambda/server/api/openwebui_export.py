"""Open WebUI export REST API endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import logging

from server.projects.openwebui_export.models import (
    ConversationExportRequest,
    ConversationExportResponse,
    ConversationListRequest,
    ConversationListResponse
)
from server.projects.openwebui_export.exporter import ConversationExporter
from server.projects.openwebui_export.client import OpenWebUIClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/export", response_model=ConversationExportResponse)
async def export_conversation(request: ConversationExportRequest):
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
    exporter = ConversationExporter()
    try:
        result = await exporter.export_conversation(request)
        await exporter.close()
        return ConversationExportResponse(**result)
    except Exception as e:
        logger.exception(f"Failed to export conversation: {e}")
        await exporter.close()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/export/batch", response_model=List[ConversationExportResponse])
async def export_conversations_batch(requests: List[ConversationExportRequest]):
    """
    Export multiple conversations in batch.
    
    This endpoint exports multiple conversations at once, which is more efficient
    than calling the single export endpoint multiple times.
    """
    exporter = ConversationExporter()
    results = []
    
    try:
        await exporter.initialize()
        
        for request in requests:
            try:
                result = await exporter.export_conversation(request)
                results.append(ConversationExportResponse(**result))
            except Exception as e:
                logger.error(f"Failed to export conversation {request.conversation_id}: {e}")
                results.append(ConversationExportResponse(
                    success=False,
                    conversation_id=request.conversation_id,
                    message=f"Export failed: {str(e)}",
                    errors=[str(e)]
                ))
        
        await exporter.close()
        return results
        
    except Exception as e:
        logger.exception(f"Batch export failed: {e}")
        await exporter.close()
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List conversations from Open WebUI.
    
    This endpoint fetches conversations from Open WebUI API. Useful for
    discovering conversations that need to be exported.
    """
    client = OpenWebUIClient()
    try:
        conversations = await client.get_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return ConversationListResponse(
            conversations=conversations,
            total=len(conversations),
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.exception(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get a specific conversation from Open WebUI.
    
    This endpoint fetches a single conversation by ID from Open WebUI API.
    """
    client = OpenWebUIClient()
    try:
        conversation = await client.get_conversation(conversation_id)
        return conversation
    except Exception as e:
        logger.exception(f"Failed to get conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

