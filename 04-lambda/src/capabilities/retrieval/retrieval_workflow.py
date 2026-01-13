"""Retrieval workflow - orchestration for vector and graph search."""

from src.capabilities.retrieval.ai import RetrievalDeps
from src.capabilities.retrieval.schemas import (
    GraphSearchRequest,
    GraphSearchResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)


async def vector_search_workflow(
    request: VectorSearchRequest,
    deps: RetrievalDeps | None = None,
) -> VectorSearchResponse:
    """
    Execute vector search workflow.

    Args:
        request: Vector search request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Vector search response
    """
    if deps is None:
        deps = RetrievalDeps.from_settings()

    await deps.initialize()
    try:
        from pydantic_ai import RunContext
        from src.capabilities.retrieval.mongo_rag.tools import search as mongo_search

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await mongo_search(ctx, request)
        return result
    finally:
        await deps.cleanup()


async def graph_search_workflow(
    request: GraphSearchRequest,
    deps: RetrievalDeps | None = None,
) -> GraphSearchResponse:
    """
    Execute graph search workflow.

    Args:
        request: Graph search request
        deps: Optional dependencies. If None, creates from settings

    Returns:
        Graph search response
    """
    if deps is None:
        deps = RetrievalDeps.from_settings()

    await deps.initialize()
    try:
        from pydantic_ai import RunContext
        from src.capabilities.retrieval.graphiti_rag.tools import search as graphiti_search

        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        result = await graphiti_search(ctx, request)
        return result
    finally:
        await deps.cleanup()


__all__ = [
    "graph_search_workflow",
    "vector_search_workflow",
]
