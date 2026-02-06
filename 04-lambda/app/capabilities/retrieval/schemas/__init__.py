"""Retrieval capability schemas.

Pydantic models for vector search, graph search, and RAG operations.
"""

from typing import Any

from pydantic import BaseModel, Field


# Vector Search Schemas
class VectorSearchRequest(BaseModel):
    """Vector search request model."""

    query: str = Field(..., description="Search query text")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    search_type: str = Field(
        default="hybrid",
        pattern="^(semantic|text|hybrid)$",
        description="Type of search to perform",
    )
    source_type: str | None = Field(
        None, description="Filter by source type (e.g., 'openwebui_conversation')"
    )
    user_id: str | None = Field(None, description="Filter by user ID")
    conversation_id: str | None = Field(None, description="Filter by conversation ID")
    topics: list[str] | None = Field(None, description="Filter by topics")


class SearchResult(BaseModel):
    """Single search result."""

    chunk_id: str
    document_id: str
    content: str
    similarity: float
    document_title: str
    document_source: str
    metadata: dict[str, Any] = {}


class VectorSearchResponse(BaseModel):
    """Vector search response model."""

    query: str
    results: list[dict[str, Any]]
    count: int
    citations: list[dict[str, Any]] | None = Field(None, description="Extracted citations")


# Graph Search Schemas
class GraphSearchRequest(BaseModel):
    """Graph search request model."""

    query: str = Field(..., description="Search query text")
    match_count: int = Field(10, ge=1, le=50, description="Number of results to return")


class GraphSearchResponse(BaseModel):
    """Graph search response model."""

    success: bool
    query: str
    results: list[dict[str, Any]]
    count: int


# Repository Parsing
class ParseRepositoryRequest(BaseModel):
    """Request model for parsing a GitHub repository."""

    repo_url: str = Field(..., description="GitHub repository URL (must end with .git)")


class ParseRepositoryResponse(BaseModel):
    """Response model for repository parsing."""

    success: bool
    message: str
    repo_url: str


# Script Validation
class ValidateScriptRequest(BaseModel):
    """Request model for script validation."""

    script_path: str = Field(..., description="Absolute path to the Python script to validate")


class ValidateScriptResponse(BaseModel):
    """Response model for script validation."""

    success: bool
    overall_confidence: float
    validation_summary: str
    hallucinations_detected: list[dict[str, Any]]


__all__ = [
    # Vector Search
    "VectorSearchRequest",
    "VectorSearchResponse",
    "SearchResult",
    # Graph Search
    "GraphSearchRequest",
    "GraphSearchResponse",
    # Repository Parsing
    "ParseRepositoryRequest",
    "ParseRepositoryResponse",
    # Script Validation
    "ValidateScriptRequest",
    "ValidateScriptResponse",
]
