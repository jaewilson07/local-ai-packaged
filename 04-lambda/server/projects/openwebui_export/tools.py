"""Core capability functions for Open WebUI export operations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic_ai import RunContext
from bson import ObjectId

from server.projects.openwebui_export.dependencies import OpenWebUIExportDeps
from server.projects.openwebui_export.models import ConversationExportRequest, ConversationMessage
from server.projects.openwebui_export.config import config
from server.projects.mongo_rag.ingestion.chunker import create_chunker, ChunkingConfig
from server.projects.mongo_rag.ingestion.embedder import create_embedder

logger = logging.getLogger(__name__)


def _format_conversation_text(messages: List[ConversationMessage]) -> str:
    """
    Format conversation messages into a single text document.
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Formatted text string
    """
    formatted_parts = []
    for msg in messages:
        role = msg.role.capitalize()
        content = msg.content.strip()
        formatted_parts.append(f"{role}: {content}\n")
    return "\n".join(formatted_parts)


async def export_conversation(
    ctx: RunContext[OpenWebUIExportDeps],
    request: ConversationExportRequest
) -> Dict[str, Any]:
    """
    Export a conversation to MongoDB RAG system.
    
    Args:
        ctx: Agent runtime context with dependencies
        request: Conversation export request
        
    Returns:
        Dictionary with export results
    """
    deps = ctx.deps
    if not deps.mongo_client:
        await deps.initialize()
    
    try:
        # Initialize chunker and embedder
        chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.chunk_size * 2,
            max_tokens=512
        )
        chunker = create_chunker(chunker_config)
        embedder = create_embedder()
        
        # Format conversation as text
        conversation_text = _format_conversation_text(request.messages)
        
        # Create document metadata
        document_metadata = {
            "source": "openwebui_conversation",
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "title": request.title or f"Conversation {request.conversation_id}",
            "topics": request.topics or [],
            "message_count": len(request.messages),
            "exported_at": datetime.utcnow().isoformat(),
            **request.metadata
        }
        
        # Chunk the conversation
        chunks = await chunker.chunk_document(
            content=conversation_text,
            title=document_metadata["title"],
            source="openwebui_conversation",
            metadata=document_metadata
        )
        logger.info(f"Created {len(chunks)} chunks from conversation {request.conversation_id}")
        
        # Generate embeddings for chunks
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await embedder.embed_batch(chunk_texts)
        
        # Create document record
        document = {
            "title": document_metadata["title"],
            "source": "openwebui_conversation",
            "content": conversation_text,
            "metadata": document_metadata,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert document
        db = deps.db
        documents_collection = db[config.mongodb_collection_documents]
        document_result = await documents_collection.insert_one(document)
        document_id = str(document_result.inserted_id)
        
        # Insert chunks with embeddings
        chunks_collection = db[config.mongodb_collection_chunks]
        chunk_documents = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_doc = {
                "document_id": document_result.inserted_id,
                "chunk_number": i,
                "content": chunk.content,
                "embedding": embedding,
                "metadata": {
                    **document_metadata,
                    **chunk.metadata,
                    "chunk_index": i,
                    "chunk_start": chunk.start_char,
                    "chunk_end": chunk.end_char
                },
                "created_at": datetime.utcnow()
            }
            chunk_documents.append(chunk_doc)
        
        if chunk_documents:
            await chunks_collection.insert_many(chunk_documents)
        
        logger.info(
            f"Exported conversation {request.conversation_id} to RAG: "
            f"document_id={document_id}, chunks={len(chunks)}"
        )
        
        return {
            "success": True,
            "conversation_id": request.conversation_id,
            "document_id": document_id,
            "chunks_created": len(chunks),
            "message": "Conversation exported successfully",
            "errors": []
        }
        
    except Exception as e:
        logger.exception(f"Failed to export conversation {request.conversation_id}: {e}")
        return {
            "success": False,
            "conversation_id": request.conversation_id,
            "document_id": None,
            "chunks_created": 0,
            "message": f"Export failed: {str(e)}",
            "errors": [str(e)]
        }


async def get_conversations(
    ctx: RunContext[OpenWebUIExportDeps],
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get list of conversations from Open WebUI.
    
    Args:
        ctx: Agent runtime context with dependencies
        user_id: Filter by user ID (optional)
        limit: Maximum number of conversations to return
        offset: Offset for pagination
        
    Returns:
        Dictionary with conversations list and metadata
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        params = {"limit": limit, "offset": offset}
        if user_id:
            params["user_id"] = user_id
        
        base_url = f"{deps.openwebui_api_url.rstrip('/')}/api/v1"
        response = await deps.http_client.get(
            f"{base_url}/conversations",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        conversations = data.get("items", [])
        
        return {
            "conversations": conversations,
            "total": len(conversations),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.exception(f"Failed to get conversations: {e}")
        return {
            "conversations": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        }


async def get_conversation(
    ctx: RunContext[OpenWebUIExportDeps],
    conversation_id: str
) -> Dict[str, Any]:
    """
    Get a specific conversation by ID from Open WebUI.
    
    Args:
        ctx: Agent runtime context with dependencies
        conversation_id: Conversation ID
        
    Returns:
        Dictionary with conversation data
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        base_url = f"{deps.openwebui_api_url.rstrip('/')}/api/v1"
        response = await deps.http_client.get(
            f"{base_url}/conversations/{conversation_id}"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.exception(f"Failed to get conversation {conversation_id}: {e}")
        return {"error": str(e)}


async def export_conversations_batch(
    ctx: RunContext[OpenWebUIExportDeps],
    requests: List[ConversationExportRequest]
) -> List[Dict[str, Any]]:
    """
    Export multiple conversations in batch.
    
    Args:
        ctx: Agent runtime context with dependencies
        requests: List of conversation export requests
        
    Returns:
        List of export result dictionaries
    """
    results = []
    for request in requests:
        result = await export_conversation(ctx, request)
        results.append(result)
    return results
