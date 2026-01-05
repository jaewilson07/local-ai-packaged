"""Graph builder adapter for ingesting MongoDB documents into Graphiti."""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from bson import ObjectId

if TYPE_CHECKING:
    from graphiti_core import Graphiti
else:
    try:
        from graphiti_core import Graphiti
    except ImportError:
        Graphiti = None  # type: ignore

from server.projects.mongo_rag.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)


async def ingest_to_graphiti(
    graphiti: Graphiti,
    document_id: str,
    chunks: List[DocumentChunk],
    metadata: Dict[str, Any],
    title: Optional[str] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ingest document chunks into Graphiti knowledge graph.
    
    Graphiti automatically extracts entities and relationships from the text
    and creates nodes and relationships in Neo4j. We link Graphiti facts to
    MongoDB chunk IDs for retrieval.
    
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
        logger.warning("Graphiti client not available - skipping ingestion")
        return {"facts_added": 0, "chunks_processed": 0}
    
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
            facts = await graphiti.add_facts(
                text=chunk.content,
                metadata=fact_metadata
            )
            
            if facts:
                facts_added += len(facts)
                chunks_processed += 1
                logger.debug(
                    f"Added {len(facts)} facts from chunk {chunk.index} "
                    f"of document {document_id}"
                )
            else:
                logger.warning(
                    f"No facts extracted from chunk {chunk.index} "
                    f"of document {document_id}"
                )
                chunks_processed += 1
                
        except Exception as e:
            error_msg = f"Error ingesting chunk {chunk.index}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    result = {
        "facts_added": facts_added,
        "chunks_processed": chunks_processed,
        "total_chunks": len(chunks),
        "errors": errors
    }
    
    logger.info(
        f"Graphiti ingestion complete for document {document_id}: "
        f"{facts_added} facts from {chunks_processed}/{len(chunks)} chunks"
    )
    
    return result

