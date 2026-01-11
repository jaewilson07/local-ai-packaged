"""Core capability functions for Crawl4AI RAG operations."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic_ai import RunContext

from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.services.crawler import crawl_single_page, crawl_deep
from server.projects.crawl4ai_rag.ingestion.adapter import CrawledContentIngester
from server.projects.mongo_rag.ingestion.pipeline import IngestionResult

logger = logging.getLogger(__name__)


async def crawl_and_ingest_single_page(
    ctx: RunContext[Crawl4AIDependencies],
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, Any]:
    """
    Crawl a single web page and ingest it into MongoDB RAG.
    
    This function performs both crawling and ingestion in one operation.
    It crawls the page, chunks it, generates embeddings, and stores it in MongoDB.
    
    Args:
        ctx: Run context with Crawl4AIDependencies
        url: URL to crawl
        chunk_size: Chunk size for document splitting
        chunk_overlap: Chunk overlap size
        
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
    
    # Ensure dependencies are initialized
    if not deps.crawler or not deps.mongo_client:
        await deps.initialize()
    
    try:
        # Phase 1: Crawl the page
        logger.info(f"🚀 Starting crawl phase for single page: {url}")
        crawl_start_time = datetime.now()
        
        result = await crawl_single_page(deps.crawler, url)
        
        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(f"✅ Crawl phase complete in {crawl_duration:.2f}s")
        
        if not result:
            return {
                'success': False,
                'url': url,
                'pages_crawled': 0,
                'chunks_created': 0,
                'document_id': None,
                'errors': [f"Failed to crawl URL: {url}"]
            }
        
        # Phase 2: Ingest into MongoDB
        logger.info(f"💾 Starting storage phase: ingesting page into MongoDB/Graphiti")
        storage_start_time = datetime.now()
        
        ingester = CrawledContentIngester(
            mongo_client=deps.mongo_client,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Initialize Graphiti if enabled
        await ingester.initialize()
        
        ingestion_result = await ingester.ingest_crawled_page(
            url=result['url'],
            markdown=result['markdown'],
            html=result.get('html'),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            crawl_metadata=result.get('metadata')
        )
        
        storage_duration = (datetime.now() - storage_start_time).total_seconds()
        logger.info(f"✅ Storage phase complete in {storage_duration:.2f}s")
        
        return {
            'success': len(ingestion_result.errors) == 0,
            'url': url,
            'pages_crawled': 1,
            'chunks_created': ingestion_result.chunks_created,
            'document_id': ingestion_result.document_id,
            'errors': ingestion_result.errors
        }
        
    except Exception as e:
        logger.exception(f"Error in crawl_and_ingest_single_page: {e}")
        return {
            'success': False,
            'url': url,
            'pages_crawled': 0,
            'chunks_created': 0,
            'document_id': None,
            'errors': [str(e)]
        }


async def crawl_and_ingest_deep(
    ctx: RunContext[Crawl4AIDependencies],
    start_url: str,
    max_depth: int,
    allowed_domains: Optional[List[str]] = None,
    allowed_subdomains: Optional[List[str]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """
    Deep crawl a website and ingest all discovered pages into MongoDB RAG.
    
    This function performs a recursive crawl starting from a URL, following internal links
    up to a specified depth. All discovered pages are automatically chunked, embedded, and
    stored in MongoDB.
    
    Args:
        ctx: Run context with Crawl4AIDependencies
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth (1-10)
        allowed_domains: List of allowed domains (exact match)
        allowed_subdomains: List of allowed subdomain prefixes
        chunk_size: Chunk size for document splitting
        chunk_overlap: Chunk overlap size
        max_concurrent: Maximum concurrent browser sessions
        
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
    
    # Ensure dependencies are initialized
    if not deps.crawler or not deps.mongo_client:
        await deps.initialize()
    
    try:
        # Phase 1: Perform deep crawl
        logger.info(f"🚀 Starting crawl phase for {start_url} (max_depth={max_depth})")
        crawl_start_time = datetime.now()
        
        crawled_pages = await crawl_deep(
            crawler=deps.crawler,
            start_url=start_url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            max_concurrent=max_concurrent
        )
        
        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(
            f"✅ Crawl phase complete: {len(crawled_pages)} pages crawled in {crawl_duration:.2f}s"
        )
        
        if not crawled_pages:
            return {
                'success': False,
                'url': start_url,
                'pages_crawled': 0,
                'chunks_created': 0,
                'document_ids': [],
                'errors': [f"No pages crawled from URL: {start_url}"]
            }
        
        # Phase 2: Ingest all pages into MongoDB
        logger.info(f"💾 Starting storage phase: ingesting {len(crawled_pages)} pages into MongoDB/Graphiti")
        storage_start_time = datetime.now()
        
        ingester = CrawledContentIngester(
            mongo_client=deps.mongo_client,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Initialize Graphiti if enabled
        await ingester.initialize()
        
        ingestion_results = await ingester.ingest_crawled_batch(
            pages=crawled_pages,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        storage_duration = (datetime.now() - storage_start_time).total_seconds()
        logger.info(
            f"✅ Storage phase complete: {len(ingestion_results)} pages ingested in {storage_duration:.2f}s"
        )
        
        # Aggregate results
        total_chunks = sum(r.chunks_created for r in ingestion_results)
        document_ids = [r.document_id for r in ingestion_results if r.document_id]
        all_errors = []
        for r in ingestion_results:
            all_errors.extend(r.errors)
        
        success = len(document_ids) > 0 and len(all_errors) == 0
        
        return {
            'success': success,
            'url': start_url,
            'pages_crawled': len(crawled_pages),
            'chunks_created': total_chunks,
            'document_ids': document_ids,
            'errors': all_errors
        }
        
    except Exception as e:
        logger.exception(f"Error in crawl_and_ingest_deep: {e}")
        return {
            'success': False,
            'url': start_url,
            'pages_crawled': 0,
            'chunks_created': 0,
            'document_ids': [],
            'errors': [str(e)]
        }
