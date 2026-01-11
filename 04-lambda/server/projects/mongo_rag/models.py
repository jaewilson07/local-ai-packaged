"""Pydantic models for RAG API."""

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query text")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    search_type: str = Field(
        default="hybrid",
        pattern="^(semantic|text|hybrid)$",
        description="Type of search to perform",
    )
    # Conversation filtering
    source_type: str | None = Field(
        None, description="Filter by source type (e.g., 'openwebui_conversation')"
    )
    user_id: str | None = Field(None, description="Filter by user ID (for conversations)")
    conversation_id: str | None = Field(None, description="Filter by conversation ID")
    topics: list[str] | None = Field(None, description="Filter by topics (for conversations)")


class SearchResult(BaseModel):
    """Single search result."""

    chunk_id: str
    document_id: str
    content: str
    similarity: float
    document_title: str
    document_source: str
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    results: list[dict[str, Any]]  # Will contain SearchResult dicts
    count: int
    citations: list[dict[str, Any]] | None = Field(None, description="Extracted citations")


class IngestResponse(BaseModel):
    """Ingestion response model."""

    documents_processed: int
    chunks_created: int
    errors: list[list[str]] = []


class AgentRequest(BaseModel):
    """Agent query request."""

    query: str = Field(..., description="Query for the conversational agent")
    state: dict[str, Any] | None = Field(default=None, description="Optional state for the agent")


class AgentResponse(BaseModel):
    """Agent query response."""

    query: str
    response: str
    state: dict[str, Any] | None = None
