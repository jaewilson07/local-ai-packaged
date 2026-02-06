"""Core capability functions for Crawl4AI RAG operations.

This module separates crawling (data acquisition) from ingestion (data storage).
Crawling uses the local crawler service, while ingestion delegates to the
centralized ContentIngestionService in mongo_rag.

The unified ingestion uses:
- ScrapedContent model for normalized input
- ContentIngestionService.ingest_scraped_content() for processing
- Graphiti episodes for temporal anchoring
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.capabilities.retrieval.mongo_rag.ingestion.content_service import ContentIngestionService
from pydantic_ai import RunContext
from app.services.compute.crawl4ai import crawl_deep, crawl_single_page
from app.workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies

from shared.models import IngestionOptions, ScrapedContent

logger = logging.getLogger(__name__)


def _build_web_metadata(url: str, crawl_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build metadata dictionary for web content.

    Args:
        url: The crawled URL
        crawl_metadata: Optional metadata from crawl4ai crawler

    Returns:
        Metadata dictionary for storage
    """
    parsed = urlparse(url)
    metadata = {
        "domain": parsed.netloc,
        "path": parsed.path,
        "scheme": parsed.scheme,
    }

    if crawl_metadata:
        # Copy relevant crawl metadata
        for key in [
            "page_title",
            "page_description",
            "page_language",
            "page_keywords",
            "page_author",
            "og_title",
            "og_description",
            "og_image",
            "crawl_timestamp",
            "crawl_depth",
            "parent_url",
            "link_counts",
            "image_count",
            "media_count",
        ]:
            if key in crawl_metadata:
                metadata[key] = crawl_metadata[key]

    return metadata


def _extract_title_from_metadata(
    url: str, markdown: str, crawl_metadata: dict[str, Any] | None = None
) -> str:
    """
    Extract title from crawl metadata or markdown content.

    Args:
        url: The crawled URL (fallback)
        markdown: The markdown content
        crawl_metadata: Optional metadata from crawler

    Returns:
        Document title
    """
    # Try crawl metadata first
    if crawl_metadata:
        if crawl_metadata.get("page_title"):
            return crawl_metadata["page_title"]
        if crawl_metadata.get("og_title"):
            return crawl_metadata["og_title"]

    # Try markdown H1
    for line in markdown.split("\n")[:10]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()

    # Fallback to URL path
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path:
        return path.split("/")[-1].replace("-", " ").replace("_", " ").title()

    return parsed.netloc


async def crawl_and_ingest_single_page(
    ctx: RunContext[Crawl4AIDependencies],
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """
    Crawl a single web page and ingest it into MongoDB RAG.

    This function performs both crawling and ingestion in one operation:
    - Phase 1: Crawl the page using crawl4ai (data acquisition)
    - Phase 2: Ingest via ContentIngestionService (centralized storage)

    Args:
        ctx: Run context with Crawl4AIDependencies
        url: URL to crawl
        chunk_size: Chunk size for document splitting
        chunk_overlap: Chunk overlap size
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        user_id: Optional user ID for RLS
        user_email: Optional user email for RLS

    Returns:
        Dictionary with:
        - success: bool
        - url: str
        - pages_crawled: int (always 1)
        - chunks_created: int
        - document_id: Optional[str]
        - errors: List[str]
    """
    deps = ctx.deps

    # Ensure crawler is initialized
    if not deps.crawler:
        await deps.initialize()

    try:
        # Phase 1: Crawl the page (data acquisition only)
        logger.info(f"🚀 Starting crawl phase for single page: {url}")
        crawl_start_time = datetime.now()

        result = await crawl_single_page(deps.crawler, url, cookies=cookies, headers=headers)

        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(f"✅ Crawl phase complete in {crawl_duration:.2f}s")

        if not result:
            return {
                "success": False,
                "url": url,
                "pages_crawled": 0,
                "chunks_created": 0,
                "document_id": None,
                "errors": [f"Failed to crawl URL: {url}"],
            }

        # Phase 2: Ingest using unified ScrapedContent pipeline
        logger.info("Starting storage phase via unified ContentIngestionService")
        storage_start_time = datetime.now()

        # Build metadata and extract title
        crawl_metadata = result.get("metadata", {})
        metadata = _build_web_metadata(url, crawl_metadata)
        title = _extract_title_from_metadata(url, result["markdown"], crawl_metadata)

        # Create ScrapedContent for unified ingestion
        scraped = ScrapedContent(
            content=result["markdown"],
            title=title,
            source=url,
            source_type="web",
            metadata=metadata,
            reference_time=datetime.now(),  # Use current time as reference
            user_id=user_id,
            user_email=user_email,
            options=IngestionOptions(
                use_docling=True,
                extract_code_examples=True,  # Web pages may have code
                create_graphiti_episode=True,  # Create temporal episode
                graphiti_episode_type="overview",
                extract_facts=True,
            ),
        )

        # Use centralized ingestion service
        service = ContentIngestionService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        try:
            await service.initialize()

            ingestion_result = await service.ingest_scraped_content(scraped)

            storage_duration = (datetime.now() - storage_start_time).total_seconds()
            logger.info(f"Storage phase complete in {storage_duration:.2f}s")

            return {
                "success": len(ingestion_result.errors) == 0,
                "url": url,
                "pages_crawled": 1,
                "chunks_created": ingestion_result.chunks_created,
                "document_id": ingestion_result.document_id,
                "errors": ingestion_result.errors,
            }
        finally:
            await service.close()

    except Exception as e:
        logger.exception("Error in crawl_and_ingest_single_page")
        return {
            "success": False,
            "url": url,
            "pages_crawled": 0,
            "chunks_created": 0,
            "document_id": None,
            "errors": [str(e)],
        }


async def crawl_and_ingest_deep(
    ctx: RunContext[Crawl4AIDependencies],
    start_url: str,
    max_depth: int,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_concurrent: int = 10,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """
    Deep crawl a website and ingest all discovered pages into MongoDB RAG.

    This function performs:
    - Phase 1: Recursive crawl using crawl4ai (data acquisition)
    - Phase 2: Batch ingest via ContentIngestionService (centralized storage)

    Args:
        ctx: Run context with Crawl4AIDependencies
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth (1-10)
        allowed_domains: List of allowed domains (exact match)
        allowed_subdomains: List of allowed subdomain prefixes
        chunk_size: Chunk size for document splitting
        chunk_overlap: Chunk overlap size
        max_concurrent: Maximum concurrent browser sessions
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        user_id: Optional user ID for RLS
        user_email: Optional user email for RLS

    Returns:
        Dictionary with:
        - success: bool
        - url: str (starting URL)
        - pages_crawled: int
        - chunks_created: int
        - document_ids: List[str]
        - errors: List[str]
    """
    deps = ctx.deps

    # Ensure crawler is initialized
    if not deps.crawler:
        await deps.initialize()

    try:
        # Phase 1: Perform deep crawl (data acquisition only)
        logger.info(f"🚀 Starting crawl phase for {start_url} (max_depth={max_depth})")
        crawl_start_time = datetime.now()

        crawled_pages = await crawl_deep(
            crawler=deps.crawler,
            start_url=start_url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            max_concurrent=max_concurrent,
            cookies=cookies,
            headers=headers,
        )

        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(
            f"✅ Crawl phase complete: {len(crawled_pages)} pages crawled in {crawl_duration:.2f}s"
        )

        if not crawled_pages:
            return {
                "success": False,
                "url": start_url,
                "pages_crawled": 0,
                "chunks_created": 0,
                "document_ids": [],
                "errors": [f"No pages crawled from URL: {start_url}"],
            }

        # Phase 2: Ingest all pages using centralized ContentIngestionService
        logger.info(
            f"💾 Starting storage phase: ingesting {len(crawled_pages)} pages via ContentIngestionService"
        )
        storage_start_time = datetime.now()

        # Use centralized ingestion service
        service = ContentIngestionService(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        try:
            await service.initialize()

            # Process pages concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(5)  # Limit concurrent ingestions
            document_ids: list[str] = []
            total_chunks = 0
            all_errors: list[str] = []

            async def ingest_page(page: dict[str, Any]) -> None:
                nonlocal total_chunks
                async with semaphore:
                    try:
                        url = page["url"]
                        markdown = page["markdown"]
                        crawl_metadata = page.get("metadata", {})

                        # Build metadata and extract title
                        metadata = _build_web_metadata(url, crawl_metadata)
                        title = _extract_title_from_metadata(url, markdown, crawl_metadata)

                        # Create ScrapedContent for unified ingestion
                        scraped = ScrapedContent(
                            content=markdown,
                            title=title,
                            source=url,
                            source_type="web",
                            metadata=metadata,
                            reference_time=datetime.now(),
                            user_id=user_id,
                            user_email=user_email,
                            options=IngestionOptions(
                                use_docling=True,
                                extract_code_examples=True,
                                create_graphiti_episode=True,
                                graphiti_episode_type="overview",
                                extract_facts=True,
                            ),
                        )

                        result = await service.ingest_scraped_content(scraped)

                        if result.document_id:
                            document_ids.append(result.document_id)
                        total_chunks += result.chunks_created
                        all_errors.extend(result.errors)

                    except Exception as e:
                        logger.exception(f"Error ingesting page {page.get('url')}")
                        all_errors.append(f"Failed to ingest {page.get('url')}: {e!s}")

            # Run all ingestions concurrently
            await asyncio.gather(*[ingest_page(page) for page in crawled_pages])

            storage_duration = (datetime.now() - storage_start_time).total_seconds()
            logger.info(
                f"✅ Storage phase complete: {len(document_ids)} pages ingested in {storage_duration:.2f}s"
            )

            success = len(document_ids) > 0 and len(all_errors) == 0

            return {
                "success": success,
                "url": start_url,
                "pages_crawled": len(crawled_pages),
                "chunks_created": total_chunks,
                "document_ids": document_ids,
                "errors": all_errors,
            }

        finally:
            await service.close()

    except Exception as e:
        logger.exception("Error in crawl_and_ingest_deep")
        return {
            "success": False,
            "url": start_url,
            "pages_crawled": 0,
            "chunks_created": 0,
            "document_ids": [],
            "errors": [str(e)],
        }


# ============================================================================
# Crawl-only functions (no ingestion) - for external callers who want to
# handle ingestion separately
# ============================================================================


async def crawl_page_only(
    ctx: RunContext[Crawl4AIDependencies],
    url: str,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """
    Crawl a single page without ingestion (data acquisition only).

    Use this when you want to handle ingestion separately via the
    /api/v1/rag/ingest/content endpoint or ContentIngestionService.

    Args:
        ctx: Run context with Crawl4AIDependencies
        url: URL to crawl
        cookies: Optional authentication cookies
        headers: Optional custom HTTP headers

    Returns:
        Dictionary with 'url', 'markdown', 'metadata', 'title' or None if failed
    """
    deps = ctx.deps

    if not deps.crawler:
        await deps.initialize()

    result = await crawl_single_page(deps.crawler, url, cookies=cookies, headers=headers)

    if not result:
        return None

    crawl_metadata = result.get("metadata", {})
    return {
        "url": result["url"],
        "markdown": result["markdown"],
        "html": result.get("html"),
        "metadata": _build_web_metadata(url, crawl_metadata),
        "title": _extract_title_from_metadata(url, result["markdown"], crawl_metadata),
    }


async def crawl_deep_only(
    ctx: RunContext[Crawl4AIDependencies],
    start_url: str,
    max_depth: int,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    max_concurrent: int = 10,
    cookies: str | dict | None = None,
    headers: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Deep crawl a website without ingestion (data acquisition only).

    Use this when you want to handle ingestion separately via the
    /api/v1/rag/ingest/content endpoint or ContentIngestionService.

    Args:
        ctx: Run context with Crawl4AIDependencies
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth
        allowed_domains: List of allowed domains
        allowed_subdomains: List of allowed subdomain prefixes
        max_concurrent: Maximum concurrent sessions
        cookies: Optional authentication cookies
        headers: Optional custom HTTP headers

    Returns:
        List of dictionaries with 'url', 'markdown', 'metadata', 'title'
    """
    deps = ctx.deps

    if not deps.crawler:
        await deps.initialize()

    crawled_pages = await crawl_deep(
        crawler=deps.crawler,
        start_url=start_url,
        max_depth=max_depth,
        allowed_domains=allowed_domains,
        allowed_subdomains=allowed_subdomains,
        max_concurrent=max_concurrent,
        cookies=cookies,
        headers=headers,
    )

    # Transform results with extracted metadata and titles
    results = []
    for page in crawled_pages:
        url = page["url"]
        markdown = page["markdown"]
        crawl_metadata = page.get("metadata", {})

        results.append(
            {
                "url": url,
                "markdown": markdown,
                "html": page.get("html"),
                "metadata": _build_web_metadata(url, crawl_metadata),
                "title": _extract_title_from_metadata(url, markdown, crawl_metadata),
            }
        )

    return results
