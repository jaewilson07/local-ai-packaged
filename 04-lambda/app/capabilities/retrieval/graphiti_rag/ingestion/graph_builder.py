"""Graph builder adapter for ingesting MongoDB documents into Graphiti.

This module provides functions for creating Graphiti episodes and extracting facts
from document content.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphiti_core import Graphiti
else:
    try:
        from graphiti_core import Graphiti
    except ImportError:
        Graphiti = None  # type: ignore

from app.capabilities.retrieval.mongo_rag.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)


def _create_overview_text(
    title: str,
    source: str,
    source_type: str,
    metadata: dict[str, Any],
    chunks: list[DocumentChunk] | None = None,
) -> str:
    """
    Create an overview episode text from document metadata.

    Args:
        title: Document title
        source: Document source URL/path
        source_type: Type of source (web, youtube, article, etc.)
        metadata: Document metadata
        chunks: Optional chunks for content summary

    Returns:
        Formatted overview text
    """
    parts = [
        f"Document Title: {title}",
        f"Source: {source}",
        f"Source Type: {source_type}",
    ]

    # Add description if available
    if metadata.get("description"):
        desc = metadata["description"][:500]
        if len(metadata.get("description", "")) > 500:
            desc += "..."
        parts.append(f"Description: {desc}")

    # Add topics if available
    if metadata.get("topics"):
        topics = metadata["topics"]
        if isinstance(topics, list):
            parts.append(f"Topics: {', '.join(topics[:10])}")

    # Add tags if available
    if metadata.get("tags"):
        tags = metadata["tags"]
        if isinstance(tags, list):
            parts.append(f"Tags: {', '.join(tags[:10])}")

    # Add channel info for YouTube
    if metadata.get("channel_name"):
        parts.append(f"Channel: {metadata['channel_name']}")

    # Add a content summary from first chunk if available
    if chunks and len(chunks) > 0:
        first_chunk_content = chunks[0].content[:300]
        if len(chunks[0].content) > 300:
            first_chunk_content += "..."
        parts.append(f"Content Preview: {first_chunk_content}")

    return "\n".join(parts)


async def create_document_episode(
    graphiti: Graphiti,
    document_id: str,
    title: str,
    source: str,
    source_type: str,
    metadata: dict[str, Any],
    reference_time: datetime,
    chunks: list[DocumentChunk] | None = None,
) -> dict[str, Any]:
    """
    Create a Graphiti episode for a document.

    Episodes provide temporal anchoring for the knowledge graph, allowing
    time-based queries and relationship tracking.

    Args:
        graphiti: Initialized Graphiti client
        document_id: MongoDB document ID
        title: Document title
        source: Document source URL/path
        source_type: Type of source (web, youtube, article, etc.)
        metadata: Document metadata
        reference_time: Temporal anchor for the episode
        chunks: Optional chunks for content summary

    Returns:
        Dictionary with episode creation result
    """
    if not graphiti:
        logger.warning("Graphiti client not available - skipping episode creation")
        return {"success": False, "error": "Graphiti not available"}

    try:
        # Import EpisodeType here to handle cases where graphiti isn't installed
        try:
            from graphiti_core import EpisodeType

            episode_type = EpisodeType.text
        except ImportError:
            logger.warning("graphiti_core not installed, using string episode type")
            episode_type = "text"

        # Create overview text
        overview_text = _create_overview_text(title, source, source_type, metadata, chunks)

        # Build source description based on source type
        source_descriptions = {
            "youtube": f"YouTube: {metadata.get('channel_name', source)}",
            "web": f"Web Page: {source}",
            "article": f"Article: {title}",
            "conversation": f"Conversation: {title}",
            "file": f"Document: {title}",
        }
        source_description = source_descriptions.get(source_type, f"Document: {source}")

        # Create the episode
        await graphiti.add_episode(
            name=f"doc:{document_id}:overview",
            episode_body=overview_text,
            source=episode_type,
            source_description=source_description,
            reference_time=reference_time,
        )

        logger.info(f"Created overview episode for document {document_id}")
        return {"success": True, "episode_name": f"doc:{document_id}:overview"}

    except Exception as e:
        error_msg = f"Error creating document episode: {e!s}"
        logger.exception(error_msg)
        return {"success": False, "error": error_msg}


async def ingest_to_graphiti(
    graphiti: Graphiti,
    document_id: str,
    chunks: list[DocumentChunk],
    metadata: dict[str, Any],
    title: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """
    Ingest document chunks into Graphiti knowledge graph as facts.

    Graphiti automatically extracts entities and relationships from the text
    and creates nodes and relationships in Neo4j. We link Graphiti facts to
    MongoDB chunk IDs for retrieval.

    Note: This function extracts facts only. For temporal anchoring,
    use create_document_episode() first.

    Args:
        graphiti: Initialized Graphiti client
        document_id: MongoDB document ID
        chunks: List of document chunks to ingest
        metadata: Document metadata
        title: Document title (optional)
        source: Document source path (optional)

    Returns:
        Dictionary with ingestion statistics
    """
    if not graphiti:
        logger.warning("Graphiti client not available - skipping fact ingestion")
        return {"facts_added": 0, "chunks_processed": 0, "errors": []}

    facts_added = 0
    chunks_processed = 0
    errors = []

    for chunk in chunks:
        try:
            # Prepare metadata for Graphiti
            # Graphiti will extract entities and relationships automatically
            fact_metadata = {
                "chunk_id": str(chunk.index),  # Use chunk index as identifier
                "document_id": document_id,
                "chunk_index": chunk.index,
                "source": source or metadata.get("source", "unknown"),
                "title": title or metadata.get("title", "Untitled"),
            }

            # Add any additional metadata
            if chunk.metadata:
                fact_metadata.update(chunk.metadata)

            # Add facts to Graphiti
            # Graphiti's add_facts automatically:
            # - Extracts entities from text
            # - Infers relationships
            # - Creates temporal facts
            # - Links to source nodes
            facts = await graphiti.add_facts(text=chunk.content, metadata=fact_metadata)

            if facts:
                facts_added += len(facts)
                chunks_processed += 1
                logger.debug(
                    f"Added {len(facts)} facts from chunk {chunk.index} of document {document_id}"
                )
            else:
                logger.warning(
                    f"No facts extracted from chunk {chunk.index} of document {document_id}"
                )
                chunks_processed += 1

        except Exception as e:
            error_msg = f"Error ingesting chunk {chunk.index}: {e!s}"
            logger.exception(error_msg)
            errors.append(error_msg)

    result = {
        "facts_added": facts_added,
        "chunks_processed": chunks_processed,
        "total_chunks": len(chunks),
        "errors": errors,
    }

    logger.info(
        f"Graphiti fact ingestion complete for document {document_id}: "
        f"{facts_added} facts from {chunks_processed}/{len(chunks)} chunks"
    )

    return result
