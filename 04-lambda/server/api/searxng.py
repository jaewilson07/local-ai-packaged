"""SearXNG web search REST API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import logging
from server.config import settings

router = APIRouter(prefix="/api/v1/searxng", tags=["searxng"])
logger = logging.getLogger(__name__)

# SearXNG URL from settings
SEARXNG_URL = settings.searxng_url


class SearXNGSearchRequest(BaseModel):
    """Request model for SearXNG search."""
    query: str = Field(..., description="Search query string")
    result_count: int = Field(10, ge=1, le=20, description="Number of results to return (1-20)")
    categories: Optional[str] = Field(None, description="Filter by category (general, news, images, etc.)")
    engines: Optional[List[str]] = Field(None, description="Filter by specific search engines")


class SearXNGSearchResult(BaseModel):
    """Individual search result from SearXNG."""
    title: str
    url: str
    content: str
    engine: Optional[str] = None
    score: Optional[float] = None


class SearXNGSearchResponse(BaseModel):
    """Response model for SearXNG search."""
    query: str
    results: List[SearXNGSearchResult]
    count: int
    success: bool = True


@router.post("/search", response_model=SearXNGSearchResponse)
async def search(request: SearXNGSearchRequest):
    """
    Search the web using SearXNG metasearch engine.
    
    SearXNG aggregates results from multiple search engines and returns
    ranked, deduplicated results. Use this for current information, real-time
    data, or information not available in the knowledge base.
    
    **Use Cases:**
    - Current events and news
    - Real-time information
    - Information not in knowledge base
    - Multi-engine search aggregation
    
    **Request Body:**
    ```json
    {
        "query": "latest AI developments",
        "result_count": 10,
        "categories": "general"
    }
    ```
    
    **Response:**
    ```json
    {
        "query": "latest AI developments",
        "success": true,
        "count": 10,
        "results": [
            {
                "title": "AI News Article",
                "url": "https://example.com/article",
                "content": "Article snippet...",
                "engine": "google",
                "score": 0.95
            }
        ]
    }
    ```
    
    **Parameters:**
    - `query` (required): Search query string
    - `result_count` (optional, default: 10): Number of results to return (1-20)
    - `categories` (optional): Filter by category (general, news, images, etc.)
    - `engines` (optional): Filter by specific search engines
    
    **Returns:**
    - `SearXNGSearchResponse` with query, results array, and count
    - Results include title, URL, content snippet, engine, and score
    
    **Errors:**
    - `500`: If SearXNG is unavailable or request fails
    - `400`: If query is empty or invalid
    
    **Integration:**
    - Also available as MCP tool: `web_search`
    - Results can be automatically ingested to RAG for future reference
    """
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Build SearXNG API request
        params = {
            "q": request.query.strip(),
            "format": "json",
            "pageno": 1
        }
        
        # Add category filter if specified
        if request.categories:
            params["categories"] = request.categories
        
        # Add engine filter if specified
        if request.engines:
            params["engines"] = ",".join(request.engines)
        
        # Make request to SearXNG
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse SearXNG response
        # SearXNG returns results in 'results' array
        results = []
        if "results" in data:
            # Limit to requested count
            limited_results = data["results"][:request.result_count]
            
            for item in limited_results:
                result = SearXNGSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    engine=item.get("engine", None),
                    score=item.get("score", None)
                )
                results.append(result)
        
        return SearXNGSearchResponse(
            query=request.query,
            results=results,
            count=len(results),
            success=True
        )
    
    except httpx.TimeoutException:
        logger.error(f"searxng_timeout: {request.query}")
        raise HTTPException(
            status_code=504,
            detail="SearXNG request timed out. The search engine may be overloaded."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"searxng_http_error: {e.response.status_code} - {request.query}")
        raise HTTPException(
            status_code=502,
            detail=f"SearXNG returned error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"searxng_connection_error: {e} - {request.query}")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to SearXNG. Ensure the service is running and accessible."
        )
    except Exception as e:
        logger.exception(f"searxng_unexpected_error: {e} - {request.query}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during search: {str(e)}"
        )

