"""Pydantic models for Crawl4AI RAG API."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional


class CrawlSinglePageRequest(BaseModel):
    """Request model for single page crawl."""
    
    url: HttpUrl = Field(..., description="URL to crawl")
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Chunk size for document splitting")
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")


class CrawlDeepRequest(BaseModel):
    """Request model for deep crawl."""
    
    url: HttpUrl = Field(..., description="Starting URL for deep crawl")
    max_depth: int = Field(..., ge=1, le=10, description="Maximum crawl depth")
    allowed_domains: Optional[List[str]] = Field(
        default=None,
        description="List of allowed domains (exact match). If None, allows all domains from starting URL."
    )
    allowed_subdomains: Optional[List[str]] = Field(
        default=None,
        description="List of allowed subdomains (prefix match). If None, allows all subdomains."
    )
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Chunk size for document splitting")
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")


class CrawlResponse(BaseModel):
    """Response model for crawl operations."""
    
    success: bool = Field(..., description="Whether the crawl operation succeeded")
    url: str = Field(..., description="The crawled URL (or starting URL for deep crawl)")
    pages_crawled: int = Field(default=0, description="Number of pages successfully crawled")
    chunks_created: int = Field(default=0, description="Total number of chunks created")
    document_ids: List[str] = Field(default_factory=list, description="List of MongoDB document IDs created")
    errors: List[str] = Field(default_factory=list, description="List of error messages if any")

