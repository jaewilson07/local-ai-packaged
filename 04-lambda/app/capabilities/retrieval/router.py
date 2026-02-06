"""Retrieval capability REST API endpoints."""

import logging
from typing import Annotated

from app.capabilities.retrieval.ai import RetrievalDeps
from app.capabilities.retrieval.retrieval_workflow import (
    graph_search_workflow,
    vector_search_workflow,
)
from app.capabilities.retrieval.schemas import (
    GraphSearchRequest,
    GraphSearchResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)
from fastapi import APIRouter, Depends, HTTPException

from shared.dependency_factory import create_dependency_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities", "retrieval"])

# Use dependency factory to create deps getter (eliminates boilerplate)
get_retrieval_deps = create_dependency_factory(RetrievalDeps)


@router.post("/retrieval/search/vector", response_model=VectorSearchResponse)
async def vector_search_endpoint(
    request: VectorSearchRequest,
    deps: Annotated[RetrievalDeps, Depends(get_retrieval_deps)],
) -> VectorSearchResponse:
    """
    Perform vector search on ingested documents.

    This endpoint searches through vector embeddings of documents to find
    semantically similar content using MongoDB vector search.

    **Request Body:**
    ```json
    {
        "query": "authentication and security",
        "match_count": 10,
        "search_type": "hybrid",
        "source_type": "openwebui_conversation",
        "user_id": "user123",
        "topics": ["security", "api"]
    }
    ```

    **Response:**
    ```json
    {
        "query": "authentication and security",
        "results": [...],
        "count": 5,
        "citations": [...]
    }
    ```
    """
    try:
        result = await vector_search_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to perform vector search")
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


@router.post("/retrieval/search/graph", response_model=GraphSearchResponse)
async def graph_search_endpoint(
    request: GraphSearchRequest,
    deps: Annotated[RetrievalDeps, Depends(get_retrieval_deps)],
) -> GraphSearchResponse:
    """
    Perform graph search on knowledge graph.

    This endpoint searches through the knowledge graph (Neo4j/Graphiti)
    to find entity relationships and connected information.

    **Request Body:**
    ```json
    {
        "query": "users who work at companies in California",
        "match_count": 10
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "query": "users who work at companies in California",
        "results": [...],
        "count": 5
    }
    ```
    """
    try:
        result = await graph_search_workflow(request, deps)
        return result
    except Exception as e:
        logger.exception("Failed to perform graph search")
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


__all__ = [
    "get_retrieval_deps",
    "router",
]
