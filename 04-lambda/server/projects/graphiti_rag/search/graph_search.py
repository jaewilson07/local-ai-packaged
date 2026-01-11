"""Graphiti search wrapper to convert results to SearchResult format."""

import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from graphiti_core import Graphiti
    from server.projects.mongo_rag.tools import SearchResult
else:
    try:
        from graphiti_core import Graphiti
    except ImportError:
        Graphiti = None  # type: ignore

logger = logging.getLogger(__name__)


async def graphiti_search(
    graphiti: "Graphiti",
    query: str,
    match_count: int = 10
) -> List["SearchResult"]:
    """
    Search Graphiti knowledge graph and convert results to SearchResult format.
    
    Args:
        graphiti: Initialized Graphiti client
        query: Search query text
        match_count: Maximum number of results to return
    
    Returns:
        List of SearchResult objects compatible with MongoDB RAG tools
    """
    # Import here to avoid circular import
    from server.projects.mongo_rag.tools import SearchResult
    
    if not graphiti:
        logger.warning("Graphiti client not available")
        return []
    
    try:
        # Search Graphiti knowledge graph
        # Graphiti performs hybrid search (semantic + keyword + graph traversal)
        results = await graphiti.search(query, limit=match_count)
        
        # Convert Graphiti results to SearchResult format
        search_results = []
        for result in results:
            # Extract chunk_id and document_id from metadata
            # These were stored during ingestion
            metadata = getattr(result, 'metadata', {}) or {}
            chunk_id = metadata.get("chunk_id") or metadata.get("chunk_index")
            document_id = metadata.get("document_id")
            
            # Get fact text (this is what Graphiti returns)
            fact_text = getattr(result, 'fact', '') or str(result)
            
            # Get relevance score if available
            score = getattr(result, 'score', None) or getattr(result, 'similarity', 0.5)
            
            # Create SearchResult
            # Note: We may not have all fields if metadata is incomplete
            # In that case, we'll need to fetch from MongoDB using chunk_id
            search_result = SearchResult(
                chunk_id=str(chunk_id) if chunk_id else "unknown",
                document_id=str(document_id) if document_id else "unknown",
                content=fact_text,
                similarity=float(score) if score else 0.5,
                metadata=metadata,
                document_title=metadata.get("title", "Unknown"),
                document_source=metadata.get("source", "Unknown")
            )
            search_results.append(search_result)
        
        logger.info(
            f"Graphiti search returned {len(search_results)} results for query: {query}"
        )
        
        return search_results
        
    except Exception as e:
        logger.exception(f"Error searching Graphiti: {e}")
        return []

