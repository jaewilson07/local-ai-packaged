"""Crawl4AI RAG REST API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import logging

from server.projects.crawl4ai_rag.models import (
    CrawlSinglePageRequest,
    CrawlDeepRequest,
    CrawlResponse
)
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.crawler import crawl_single_page, crawl_deep
from server.projects.crawl4ai_rag.ingestion.adapter import CrawledContentIngester

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/single", response_model=CrawlResponse)
async def crawl_single(request: CrawlSinglePageRequest):
    """
    Crawl a single web page and automatically ingest it into the MongoDB RAG knowledge base.
    
    This endpoint uses crawl4ai to fetch a single webpage, extract its content as markdown,
    chunk it into manageable pieces, generate embeddings, and store everything in MongoDB.
    The crawled content becomes immediately searchable via the RAG search endpoints.
    
    **Use Cases:**
    - Quickly index a specific documentation page
    - Add a single article or blog post to the knowledge base
    - Test crawling functionality before deep crawling
    - Index individual pages from a website
    
    **Request Body:**
    ```json
    {
        "url": "https://example.com/page",
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "url": "https://example.com/page",
        "pages_crawled": 1,
        "chunks_created": 15,
        "document_ids": ["507f1f77bcf86cd799439011"],
        "errors": []
    }
    ```
    
    **Parameters:**
    - `url` (required): The URL to crawl. Must be a valid HTTP/HTTPS URL.
    - `chunk_size` (optional, default: 1000): Maximum characters per chunk. Range: 100-5000.
      Larger chunks preserve more context but may exceed embedding model limits.
    - `chunk_overlap` (optional, default: 200): Character overlap between chunks. Range: 0-500.
      Overlap helps maintain context across chunk boundaries.
    
    **Returns:**
    - `CrawlResponse` with success status, page count, chunks created, and document IDs
    
    **Errors:**
    - `500`: If crawling fails (network error, invalid URL, page not accessible, etc.)
    - `500`: If ingestion fails (MongoDB connection error, embedding generation failure)
    
    **Integration:**
    - Also available as MCP tool: `crawl_single_page`
    - Crawled content is searchable via `/api/v1/rag/search` immediately after ingestion
    - Uses same MongoDB collections as document ingestion (`documents`, `chunks`)
    - Metadata extracted includes: page title, description, language, images, links, etc.
    
    **Example Usage:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/crawl/single \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://docs.example.com/getting-started",
        "chunk_size": 1500,
        "chunk_overlap": 300
      }'
    ```
    
    **Performance Notes:**
    - Typical crawl time: 2-5 seconds per page
    - Embedding generation adds 1-3 seconds depending on content size
    - Total processing time scales with page content length
    """
    deps = Crawl4AIDependencies()
    await deps.initialize()
    
    try:
        # Phase 1: Crawl the page
        logger.info(f"🚀 Starting crawl phase for single page: {request.url}")
        crawl_start_time = datetime.now()
        
        result = await crawl_single_page(deps.crawler, str(request.url))
        
        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(f"✅ Crawl phase complete in {crawl_duration:.2f}s")
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to crawl URL: {request.url}"
            )
        
        # Phase 2: Start storage/ingestion phase
        logger.info(f"💾 Starting storage phase: ingesting page into MongoDB/Graphiti")
        storage_start_time = datetime.now()
        
        # Ingest into MongoDB
        ingester = CrawledContentIngester(
            mongo_client=deps.mongo_client,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Initialize Graphiti if enabled
        await ingester.initialize()
        
        ingestion_result = await ingester.ingest_crawled_page(
            url=result['url'],
            markdown=result['markdown'],
            html=result.get('html'),  # Pass HTML content
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            crawl_metadata=result.get('metadata')
        )
        
        storage_duration = (datetime.now() - storage_start_time).total_seconds()
        logger.info(f"✅ Storage phase complete in {storage_duration:.2f}s")
        
        if ingestion_result.errors:
            return CrawlResponse(
                success=False,
                url=str(request.url),
                pages_crawled=1,
                chunks_created=ingestion_result.chunks_created,
                document_ids=[ingestion_result.document_id] if ingestion_result.document_id else [],
                errors=ingestion_result.errors
            )
        
        return CrawlResponse(
            success=True,
            url=str(request.url),
            pages_crawled=1,
            chunks_created=ingestion_result.chunks_created,
            document_ids=[ingestion_result.document_id],
            errors=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in crawl_single: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await deps.cleanup()


@router.post("/deep", response_model=CrawlResponse)
async def crawl_deep_endpoint(request: CrawlDeepRequest):
    """
    Deep crawl a website recursively and ingest all discovered pages into MongoDB.
    
    This endpoint performs a recursive crawl starting from a URL, following internal links
    up to a specified depth. It can filter by allowed domains and subdomains to control
    crawl scope. All discovered pages are automatically chunked, embedded, and stored in
    MongoDB for immediate searchability.
    
    **Use Cases:**
    - Index entire documentation sites
    - Crawl blog archives with multiple pages
    - Build knowledge base from multi-page resources
    - Index specific sections of a website
    
    **Request Body:**
    ```json
    {
        "url": "https://docs.example.com",
        "max_depth": 3,
        "allowed_domains": ["docs.example.com"],
        "allowed_subdomains": ["api", "guides"],
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "url": "https://docs.example.com",
        "pages_crawled": 42,
        "chunks_created": 387,
        "document_ids": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012", ...],
        "errors": []
    }
    ```
    
    **Parameters:**
    - `url` (required): Starting URL for the crawl. Must be a valid HTTP/HTTPS URL.
    - `max_depth` (required): Maximum recursion depth. Range: 1-10.
      - Depth 1: Only the starting page
      - Depth 2: Starting page + pages linked from it
      - Depth 3: Starting page + 2 levels of links (recommended for most sites)
    - `allowed_domains` (optional): List of allowed domains for exact matching.
      If not provided, allows all domains from the starting URL.
      Example: `["example.com", "docs.example.com"]`
    - `allowed_subdomains` (optional): List of allowed subdomain prefixes.
      If not provided, allows all subdomains.
      Example: `["docs", "api", "blog"]` matches `docs.example.com`, `api.example.com`, etc.
    - `chunk_size` (optional, default: 1000): Maximum characters per chunk. Range: 100-5000.
    - `chunk_overlap` (optional, default: 200): Character overlap between chunks. Range: 0-500.
    
    **Domain Filtering Logic:**
    - `allowed_domains`: Exact domain match (e.g., `example.com` matches `example.com` and `www.example.com`)
    - `allowed_subdomains`: Prefix match (e.g., `docs` matches `docs.example.com`, `docs-api.example.com`)
    - If both are provided, URL must match at least one domain AND one subdomain
    - If neither provided, only URLs from the starting domain are crawled
    
    **Returns:**
    - `CrawlResponse` with aggregated results across all crawled pages
    
    **Errors:**
    - `500`: If no pages are crawled (invalid starting URL, all pages blocked by filters, etc.)
    - `500`: If ingestion fails for any pages (partial success may still return results)
    - Individual page errors are collected in the `errors` array
    
    **Integration:**
    - Also available as MCP tool: `crawl_deep`
    - All crawled pages are searchable via `/api/v1/rag/search` after ingestion
    - Uses same MongoDB collections as document ingestion (`documents`, `chunks`)
    - Each page's metadata includes crawl depth and parent URL for traceability
    
    **Example Usage:**
    ```bash
    # Crawl documentation site with depth limit
    curl -X POST http://localhost:8000/api/v1/crawl/deep \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://docs.example.com",
        "max_depth": 3,
        "allowed_domains": ["docs.example.com"],
        "chunk_size": 1000
      }'
    
    # Crawl specific subdomains only
    curl -X POST http://localhost:8000/api/v1/crawl/deep \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://example.com",
        "max_depth": 2,
        "allowed_subdomains": ["docs", "api"],
        "chunk_size": 1500
      }'
    ```
    
    **Performance Notes:**
    - Crawling runs concurrently (up to 10 pages simultaneously)
    - Typical time: 5-10 seconds per page at depth 1, scales with depth
    - Deep crawls can take minutes for large sites (100+ pages)
    - Memory usage scales with concurrent sessions and page content size
    - Consider using `max_depth=2` or `max_depth=3` for most use cases
    
    **Best Practices:**
    - Start with `max_depth=2` to test crawl behavior
    - Use `allowed_domains` to prevent crawling external sites
    - Use `allowed_subdomains` to focus on specific sections
    - Monitor `errors` array for pages that failed to crawl
    - Check `pages_crawled` vs expected count to verify filtering works
    """
    deps = Crawl4AIDependencies()
    await deps.initialize()
    
    try:
        # Phase 1: Perform deep crawl
        logger.info(f"🚀 Starting crawl phase for {request.url} (max_depth={request.max_depth})")
        crawl_start_time = datetime.now()
        
        crawled_pages = await crawl_deep(
            crawler=deps.crawler,
            start_url=str(request.url),
            max_depth=request.max_depth,
            allowed_domains=request.allowed_domains,
            allowed_subdomains=request.allowed_subdomains,
            max_concurrent=10  # Use config default
        )
        
        crawl_duration = (datetime.now() - crawl_start_time).total_seconds()
        logger.info(
            f"✅ Crawl phase complete: {len(crawled_pages)} pages crawled in {crawl_duration:.2f}s"
        )
        
        if not crawled_pages:
            raise HTTPException(
                status_code=500,
                detail=f"No pages crawled from URL: {request.url}"
            )
        
        # Phase 2: Start storage/ingestion phase
        logger.info(f"💾 Starting storage phase: ingesting {len(crawled_pages)} pages into MongoDB/Graphiti")
        storage_start_time = datetime.now()
        
        # Ingest all pages into MongoDB
        ingester = CrawledContentIngester(
            mongo_client=deps.mongo_client,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        # Initialize Graphiti if enabled
        await ingester.initialize()
        
        ingestion_results = await ingester.ingest_crawled_batch(
            pages=crawled_pages,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
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
        
        return CrawlResponse(
            success=success,
            url=str(request.url),
            pages_crawled=len(crawled_pages),
            chunks_created=total_chunks,
            document_ids=document_ids,
            errors=all_errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in crawl_deep: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await deps.cleanup()

