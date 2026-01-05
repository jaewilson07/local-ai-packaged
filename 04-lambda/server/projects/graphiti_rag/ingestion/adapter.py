"""Adapter to bridge MongoDB documents with Graphiti ingestion."""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from graphiti_core import Graphiti
else:
    try:
        from graphiti_core import Graphiti
    except ImportError:
        Graphiti = None  # type: ignore

from server.projects.mongo_rag.ingestion.chunker import DocumentChunk
from server.projects.graphiti_rag.ingestion.graph_builder import ingest_to_graphiti

logger = logging.getLogger(__name__)


class GraphitiIngestionAdapter:
    """
    Adapter to ingest MongoDB documents into Graphiti knowledge graph.
    
    This adapter takes documents that have been processed and stored in MongoDB
    and ingests them into Graphiti for knowledge graph construction.
    """
    
    def __init__(self, graphiti: Optional[Graphiti] = None):
        """
        Initialize adapter.
        
        Args:
            graphiti: Optional Graphiti client (will be initialized if not provided)
        """
        self.graphiti = graphiti
    
    async def ingest_document(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any],
        title: Optional[str] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document into Graphiti.
        
        Args:
            document_id: MongoDB document ID
            chunks: List of document chunks
            metadata: Document metadata
            title: Document title
            source: Document source path
        
        Returns:
            Ingestion statistics
        """
        if not self.graphiti:
            logger.warning("Graphiti client not available - skipping ingestion")
            return {"facts_added": 0, "chunks_processed": 0, "errors": []}
        
        return await ingest_to_graphiti(
            self.graphiti,
            document_id,
            chunks,
            metadata,
            title,
            source
        )

