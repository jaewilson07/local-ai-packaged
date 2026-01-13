"""Main Crawl4AI RAG agent implementation."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.ag_ui import StateDeps
from workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies
from workflows.ingestion.crawl4ai_rag.config import config
from workflows.ingestion.crawl4ai_rag.tools import (
    crawl_and_ingest_deep,
    crawl_and_ingest_single_page,
)

from shared.llm import get_llm_model as _get_crawl4ai_model


class Crawl4AIState(BaseModel):
    """State for Crawl4AI RAG agent."""

    current_url: str | None = None
    crawl_history: list[str] = Field(default_factory=list)
    user_preferences: dict = Field(default_factory=dict)


# Create agent with dependencies
crawl4ai_agent = Agent(
    model=_get_crawl4ai_model(),
    system_prompt="""You are a web crawling and RAG ingestion assistant.

Your role is to help users crawl websites and automatically ingest the content
into a MongoDB RAG knowledge base for searchability.

You can:
- Crawl single pages and immediately make them searchable
- Perform deep crawls of entire websites with depth control
- Filter crawls by domain and subdomain
- Automatically chunk, embed, and store crawled content

Always confirm crawl parameters (URL, depth, filters) before starting large crawls.
Provide clear feedback on crawl progress and results.""",
    deps_type=Crawl4AIDependencies,
    state_type=StateDeps[Crawl4AIState, Crawl4AIDependencies],
)


@crawl4ai_agent.tool
async def crawl_single_page_tool(
    ctx: RunContext[StateDeps[Crawl4AIState, Crawl4AIDependencies]],
    url: str = Field(..., description="URL to crawl"),
    chunk_size: int = Field(
        default=1000, ge=100, le=5000, description="Chunk size for document splitting"
    ),
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size"),
) -> dict:
    """
    Crawl a single web page and automatically ingest it into MongoDB RAG.

    This tool crawls a single webpage, extracts its content as markdown,
    chunks it, generates embeddings, and stores everything in MongoDB.
    The crawled content becomes immediately searchable.

    Args:
        url: URL to crawl (must be valid HTTP/HTTPS URL)
        chunk_size: Maximum characters per chunk (100-5000)
        chunk_overlap: Character overlap between chunks (0-500)

    Returns:
        Dictionary with success status, page count, chunks created, and document ID
    """
    # Create new context with just the dependencies
    deps_ctx = RunContext(deps=ctx.deps.deps)
    result = await crawl_and_ingest_single_page(
        deps_ctx, url=url, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    # Update state
    if result.get("success"):
        ctx.state.current_url = url
        ctx.state.crawl_history.append(url)

    return result


@crawl4ai_agent.tool
async def crawl_deep_tool(
    ctx: RunContext[StateDeps[Crawl4AIState, Crawl4AIDependencies]],
    url: str = Field(..., description="Starting URL for deep crawl"),
    max_depth: int = Field(..., ge=1, le=10, description="Maximum crawl depth"),
    allowed_domains: list[str] | None = Field(
        default=None,
        description="List of allowed domains (exact match). If None, allows all domains from starting URL.",
    ),
    allowed_subdomains: list[str] | None = Field(
        default=None,
        description="List of allowed subdomains (prefix match). If None, allows all subdomains.",
    ),
    chunk_size: int = Field(
        default=1000, ge=100, le=5000, description="Chunk size for document splitting"
    ),
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size"),
) -> dict:
    """
    Deep crawl a website recursively and ingest all discovered pages into MongoDB.

    This tool performs a recursive crawl starting from a URL, following internal links
    up to a specified depth. It can filter by allowed domains and subdomains.
    All discovered pages are automatically chunked, embedded, and stored in MongoDB.

    Args:
        url: Starting URL for the crawl
        max_depth: Maximum recursion depth (1-10)
        allowed_domains: List of allowed domains for exact matching
        allowed_subdomains: List of allowed subdomain prefixes
        chunk_size: Maximum characters per chunk (100-5000)
        chunk_overlap: Character overlap between chunks (0-500)

    Returns:
        Dictionary with success status, pages crawled, chunks created, and document IDs
    """
    # Create new context with just the dependencies
    deps_ctx = RunContext(deps=ctx.deps.deps)
    result = await crawl_and_ingest_deep(
        deps_ctx,
        start_url=url,
        max_depth=max_depth,
        allowed_domains=allowed_domains,
        allowed_subdomains=allowed_subdomains,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_concurrent=config.max_concurrent_sessions,
    )

    # Update state
    if result.get("success"):
        ctx.state.current_url = url
        ctx.state.crawl_history.append(url)

    return result


__all__ = ["Crawl4AIState", "crawl4ai_agent"]
