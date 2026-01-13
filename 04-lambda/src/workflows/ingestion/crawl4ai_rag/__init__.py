"""Crawl4AI RAG workflow module.

This module provides web crawling and RAG ingestion capabilities organized by:
- schemas/: Request/Response models
- ai/: Agent definitions and dependencies
- workflow.py: High-level orchestration functions
- router.py: FastAPI endpoints
- tools.py: Core capability functions
"""

from workflows.ingestion.crawl4ai_rag.ai import (
    Crawl4AIDependencies,
    Crawl4AIState,
    crawl4ai_agent,
)
from workflows.ingestion.crawl4ai_rag.schemas import (
    CrawlDeepRequest,
    CrawlResponse,
    CrawlSinglePageRequest,
)
from workflows.ingestion.crawl4ai_rag.workflow import (
    ingest_deep_crawl_workflow,
    ingest_single_page_workflow,
)

__all__ = [
    # Schemas
    "CrawlSinglePageRequest",
    "CrawlDeepRequest",
    "CrawlResponse",
    # AI Components
    "crawl4ai_agent",
    "Crawl4AIState",
    "Crawl4AIDependencies",
    # Workflows
    "ingest_single_page_workflow",
    "ingest_deep_crawl_workflow",
]
