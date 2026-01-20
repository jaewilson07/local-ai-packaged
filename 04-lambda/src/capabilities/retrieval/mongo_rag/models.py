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
        None, description="Filter by source type (e.g., 'openwebui_conversation', 'youtube')"
    )
    user_id: str | None = Field(None, description="Filter by user ID (for conversations)")
    conversation_id: str | None = Field(None, description="Filter by conversation ID")
    topics: list[str] | None = Field(None, description="Filter by topics (for conversations)")
    # Project scope filtering
    project_scope: str | None = Field(
        None, description="Filter by project scope (e.g., 'comfyui-lora-research')"
    )
    tags: list[str] | None = Field(None, description="Filter by tags")
    # Generic metadata filter
    metadata_filter: dict[str, Any] | None = Field(None, description="Additional metadata filters")


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


class IngestContentRequest(BaseModel):
    """Request for ingesting arbitrary content (not file upload)."""

    content: str = Field(..., description="Markdown or plain text content to ingest")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Source URL or identifier")
    source_type: str = Field(
        default="custom",
        description="Type of source: 'web', 'youtube', 'article', 'custom'",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    use_docling: bool = Field(
        default=True,
        description="Parse through Docling for structure-aware chunking",
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Skip if content from this source already exists",
    )


class IngestContentResponse(BaseModel):
    """Response for content ingestion."""

    success: bool
    document_id: str = ""
    title: str = ""
    source: str = ""
    source_type: str = ""
    chunks_created: int = 0
    processing_time_ms: float = 0
    skipped: bool = False
    skip_reason: str = ""
    errors: list[str] = []
