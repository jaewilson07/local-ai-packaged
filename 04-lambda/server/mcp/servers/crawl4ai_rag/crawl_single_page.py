"""Crawl a single web page and automatically ingest it into the MongoDB RAG knowledge base. The page becomes immediately searchable via search endpoints. Extracts page metadata including title, description, language, images, and links."""
from typing import Optional, List, Any, Literal
from server.mcp.servers.client import call_mcp_tool

async def crawl_single_page(
    url: str, chunk_size: Optional[int] = 1000, chunk_overlap: Optional[int] = 200
) -> dict:
    """
    Crawl a single web page and automatically ingest it into the MongoDB RAG knowledge base. The page becomes immediately searchable via search endpoints. Extracts page metadata including title, description, language, images, and links.
    
    Args:
        url (str): URL to crawl. Must be a valid HTTP/HTTPS URL. Required.
        chunk_size (int): Chunk size for document splitting. Range: 100-5000. Larger chunks preserve more context but may exceed embedding model limits. Default: 1000.
        chunk_overlap (int): Chunk overlap size. Range: 0-500. Overlap helps maintain context across chunk boundaries. Default: 200.
    
    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "crawl_single_page",
        {
            "url": url,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
    )
