"""Retrieval agent for vector and graph search."""

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from src.capabilities.retrieval.ai.dependencies import RetrievalDeps
from src.shared.llm import get_llm_model


class RetrievalState(BaseModel):
    """Shared state for retrieval agents."""


# Create the retrieval agent
retrieval_agent = Agent(
    get_llm_model(),
    deps_type=RetrievalDeps,
    system_prompt=(
        "You are an expert retrieval agent that helps search and find relevant information. "
        "You can perform vector searches for semantic similarity and graph searches for relationship-based queries. "
        "Always provide clear, relevant results with proper citations."
    ),
)


@retrieval_agent.tool
async def vector_search(
    ctx: RunContext[RetrievalDeps],
    query: str,
    match_count: int = 5,
    search_type: str = "hybrid",
) -> str:
    """
    Perform vector search on ingested documents.

    This tool searches through vector embeddings of documents to find
    semantically similar content.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (1-50)
        search_type: Type of search - 'semantic', 'text', or 'hybrid'

    Returns:
        String describing the search results
    """
    # Import here to avoid circular dependencies
    from src.capabilities.retrieval.mongo_rag.tools import search as mongo_search

    deps = ctx.deps
    if not deps.db:
        await deps.initialize()

    from src.capabilities.retrieval.schemas import VectorSearchRequest

    request = VectorSearchRequest(
        query=query,
        match_count=min(match_count, 50),
        search_type=search_type,
    )

    result = await mongo_search(ctx, request)
    return f"Vector search found {result.count} results for '{query}': {result.results[:3]}"


@retrieval_agent.tool
async def graph_search(
    ctx: RunContext[RetrievalDeps],
    query: str,
    match_count: int = 10,
) -> str:
    """
    Perform graph search on knowledge graph.

    This tool searches through the knowledge graph (Neo4j/Graphiti)
    to find entity relationships and connected information.

    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return

    Returns:
        String describing the graph search results
    """
    # Import here to avoid circular dependencies
    from src.capabilities.retrieval.graphiti_rag.tools import search as graphiti_search

    deps = ctx.deps
    if deps.graphiti_deps:
        await deps.graphiti_deps.initialize()

    from src.capabilities.retrieval.schemas import GraphSearchRequest

    request = GraphSearchRequest(
        query=query,
        match_count=min(match_count, 50),
    )

    result = await graphiti_search(ctx, request)
    return f"Graph search found {result.count} results for '{query}': {result.results[:3]}"


__all__ = [
    "RetrievalState",
    "graph_search",
    "retrieval_agent",
    "vector_search",
]
