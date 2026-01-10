"""Crawl4AI RAG REST API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
import logging
from pydantic_ai import RunContext

from server.core.api_utils import with_dependencies
from server.projects.crawl4ai_rag.models import (
    CrawlSinglePageRequest,
    CrawlDeepRequest,
    CrawlResponse
)
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import (
    crawl_and_ingest_single_page,
    crawl_and_ingest_deep
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/single", response_model=CrawlResponse)
@with_dependencies(Crawl4AIDependencies)
async def crawl_single(request: CrawlSinglePageRequest, deps: Crawl4AIDependencies):
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
    try:
        # Use tools.py function with RunContext
        ctx = RunContext(deps=deps)
        result = await crawl_and_ingest_single_page(
            ctx,
            url=str(request.url),
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        return CrawlResponse(
            success=result['success'],
            url=result['url'],
            pages_crawled=result['pages_crawled'],
            chunks_created=result['chunks_created'],
            document_ids=[result['document_id']] if result.get('document_id') else [],
            errors=result.get('errors', [])
        )
        
    except Exception as e:
        logger.exception(f"Error in crawl_single: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deep", response_model=CrawlResponse)
@with_dependencies(Crawl4AIDependencies)
async def crawl_deep_endpoint(request: CrawlDeepRequest, deps: Crawl4AIDependencies):
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
    try:
        # Use tools.py function with RunContext
        ctx = RunContext(deps=deps)
        result = await crawl_and_ingest_deep(
            ctx,
            start_url=str(request.url),
            max_depth=request.max_depth,
            allowed_domains=request.allowed_domains,
            allowed_subdomains=request.allowed_subdomains,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            max_concurrent=10  # Use config default
        )
        
        return CrawlResponse(
            success=result['success'],
            url=result['url'],
            pages_crawled=result['pages_crawled'],
            chunks_created=result['chunks_created'],
            document_ids=result.get('document_ids', []),
            errors=result.get('errors', [])
        )
        
    except Exception as e:
        logger.exception(f"Error in crawl_deep: {e}")
        raise HTTPException(status_code=500, detail=str(e))

