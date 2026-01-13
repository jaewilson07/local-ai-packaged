"""Ingestion workflow orchestration for crawl4ai_rag.

This module provides high-level orchestration functions that combine
crawling, chunking, embedding, and storage operations.
"""

import logging

from pydantic_ai import RunContext
from workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies
from workflows.ingestion.crawl4ai_rag.schemas import (
    CrawlDeepRequest,
    CrawlResponse,
    CrawlSinglePageRequest,
)
from workflows.ingestion.crawl4ai_rag.tools import (
    crawl_and_ingest_deep,
    crawl_and_ingest_single_page,
)

logger = logging.getLogger(__name__)


async def ingest_single_page_workflow(
    request: CrawlSinglePageRequest, user_email: str
) -> CrawlResponse:
    """
    Workflow to crawl a single page and ingest into RAG system.

    Args:
        request: Crawl request parameters
        user_email: User email for data isolation

    Returns:
        CrawlResponse with operation results
    """
    deps = Crawl4AIDependencies.from_settings(skip_mongodb=True, skip_openai=True)
    await deps.initialize()

    try:
        ctx = RunContext(deps=deps)
        result = await crawl_and_ingest_single_page(
            ctx,
            url=str(request.url),
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            cookies=request.cookies,
            headers=request.headers,
            user_email=user_email,
        )

        return CrawlResponse(
            success=result.get("success", False),
            url=result.get("url", str(request.url)),
            pages_crawled=result.get("pages_crawled", 0),
            chunks_created=result.get("chunks_created", 0),
            document_ids=result.get("document_ids", []),
            errors=result.get("errors", []),
        )
    finally:
        await deps.cleanup()


async def ingest_deep_crawl_workflow(request: CrawlDeepRequest, user_email: str) -> CrawlResponse:
    """
    Workflow to deep crawl a website and ingest all pages into RAG system.

    Args:
        request: Deep crawl request parameters
        user_email: User email for data isolation

    Returns:
        CrawlResponse with operation results
    """
    deps = Crawl4AIDependencies.from_settings(skip_mongodb=True, skip_openai=True)
    await deps.initialize()

    try:
        ctx = RunContext(deps=deps)
        result = await crawl_and_ingest_deep(
            ctx,
            start_url=str(request.url),
            max_depth=request.max_depth,
            allowed_domains=request.allowed_domains,
            allowed_subdomains=request.allowed_subdomains,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            cookies=request.cookies,
            headers=request.headers,
            user_email=user_email,
        )

        return CrawlResponse(
            success=result.get("success", False),
            url=result.get("url", str(request.url)),
            pages_crawled=result.get("pages_crawled", 0),
            chunks_created=result.get("chunks_created", 0),
            document_ids=result.get("document_ids", []),
            errors=result.get("errors", []),
        )
    finally:
        await deps.cleanup()


__all__ = ["ingest_deep_crawl_workflow", "ingest_single_page_workflow"]
