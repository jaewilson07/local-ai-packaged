"""Pydantic models for Crawl4AI RAG API."""

from pydantic import BaseModel, Field, HttpUrl


class CrawlSinglePageRequest(BaseModel):
    """Request model for single page crawl."""

    url: HttpUrl = Field(..., description="URL to crawl")
    chunk_size: int = Field(
        default=1000, ge=100, le=5000, description="Chunk size for document splitting"
    )
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")
    cookies: str | dict | None = Field(
        default=None,
        description="Optional authentication cookies as string (e.g., 'sessionid=abc123; csrftoken=xyz') or dict",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional custom HTTP headers as dict (e.g., {'Authorization': 'Bearer token'})",
    )


class CrawlDeepRequest(BaseModel):
    """Request model for deep crawl."""

    url: HttpUrl = Field(..., description="Starting URL for deep crawl")
    max_depth: int = Field(..., ge=1, le=10, description="Maximum crawl depth")
    allowed_domains: list[str] | None = Field(
        default=None,
        description="List of allowed domains (exact match). If None, allows all domains from starting URL.",
    )
    allowed_subdomains: list[str] | None = Field(
        default=None,
        description="List of allowed subdomains (prefix match). If None, allows all subdomains.",
    )
    chunk_size: int = Field(
        default=1000, ge=100, le=5000, description="Chunk size for document splitting"
    )
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")
    cookies: str | dict | None = Field(
        default=None,
        description="Optional authentication cookies as string (e.g., 'sessionid=abc123; csrftoken=xyz') or dict",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Optional custom HTTP headers as dict (e.g., {'Authorization': 'Bearer token'})",
    )


class CrawlResponse(BaseModel):
    """Response model for crawl operations."""

    success: bool = Field(..., description="Whether the crawl operation succeeded")
    url: str = Field(..., description="The crawled URL (or starting URL for deep crawl)")
    pages_crawled: int = Field(default=0, description="Number of pages successfully crawled")
    chunks_created: int = Field(default=0, description="Total number of chunks created")
    document_ids: list[str] = Field(
        default_factory=list, description="List of MongoDB document IDs created"
    )
    errors: list[str] = Field(default_factory=list, description="List of error messages if any")


__all__ = ["CrawlDeepRequest", "CrawlResponse", "CrawlSinglePageRequest"]
