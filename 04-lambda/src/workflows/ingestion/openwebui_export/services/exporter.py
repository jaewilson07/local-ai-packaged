"""Service to export Open WebUI conversations to MongoDB RAG."""

import logging
from datetime import datetime
from typing import Any

from pymongo import AsyncMongoClient

from server.projects.mongo_rag.ingestion.chunker import ChunkingConfig, create_chunker
from server.projects.mongo_rag.ingestion.embedder import create_embedder
from server.projects.openwebui_export.config import config
from server.projects.openwebui_export.models import ConversationExportRequest, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationExporter:
    """Exports Open WebUI conversations to MongoDB RAG system."""

    def __init__(self):
        """Initialize the conversation exporter."""
        self.mongo_client: AsyncMongoClient | None = None
        self.db = None

        # Initialize chunker and embedder
        chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.chunk_size * 2,
            max_tokens=512,
        )
        self.chunker = create_chunker(chunker_config)
        self.embedder = create_embedder()

    async def initialize(self):
        """Initialize MongoDB connection."""
        if not self.mongo_client:
            self.mongo_client = AsyncMongoClient(config.mongodb_uri)
            self.db = self.mongo_client[config.mongodb_database]
            logger.info("MongoDB connection initialized for conversation export")

    async def close(self):
        """Close MongoDB connection."""
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None

    def _format_conversation_text(self, messages: list[ConversationMessage]) -> str:
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

    async def export_conversation(self, request: ConversationExportRequest) -> dict[str, Any]:
        """
        Export a conversation to MongoDB RAG system.

        Args:
            request: Conversation export request

        Returns:
            Dictionary with export results
        """
        await self.initialize()

        try:
            # Format conversation as text
            conversation_text = self._format_conversation_text(request.messages)

            # Create document metadata
            document_metadata = {
                "source": "openwebui_conversation",
                "conversation_id": request.conversation_id,
                "user_id": request.user_id,
                "title": request.title or f"Conversation {request.conversation_id}",
                "topics": request.topics or [],
                "message_count": len(request.messages),
                "exported_at": datetime.utcnow().isoformat(),
                **request.metadata,
            }

            # Chunk the conversation using chunk_document method
            chunks = await self.chunker.chunk_document(
                content=conversation_text,
                title=document_metadata["title"],
                source="openwebui_conversation",
                metadata=document_metadata,
            )
            logger.info(f"Created {len(chunks)} chunks from conversation {request.conversation_id}")

            # Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedder.embed_batch(chunk_texts)

            # Create document record
            document = {
                "title": document_metadata["title"],
                "source": "openwebui_conversation",
                "content": conversation_text,
                "metadata": document_metadata,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Insert document
            documents_collection = self.db[config.mongodb_collection_documents]
            document_result = await documents_collection.insert_one(document)
            document_id = str(document_result.inserted_id)

            # Insert chunks with embeddings
            chunks_collection = self.db[config.mongodb_collection_chunks]
            chunk_documents = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
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
                        "chunk_end": chunk.end_char,
                    },
                    "created_at": datetime.utcnow(),
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
                "errors": [],
            }

        except Exception as e:
            logger.exception("Failed to export conversation {request.conversation_id}")
            return {
                "success": False,
                "conversation_id": request.conversation_id,
                "document_id": None,
                "chunks_created": 0,
                "message": f"Export failed: {e!s}",
                "errors": [str(e)],
            }
