"""Pydantic models for RAG API."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query text")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    search_type: str = Field(default="hybrid", pattern="^(semantic|text|hybrid)$", description="Type of search to perform")
    # Conversation filtering
    source_type: Optional[str] = Field(None, description="Filter by source type (e.g., 'openwebui_conversation')")
    user_id: Optional[str] = Field(None, description="Filter by user ID (for conversations)")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation ID")
    topics: Optional[List[str]] = Field(None, description="Filter by topics (for conversations)")


class SearchResult(BaseModel):
    """Single search result."""
    chunk_id: str
    document_id: str
    content: str
    similarity: float
    document_title: str
    document_source: str
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: List[Dict[str, Any]]  # Will contain SearchResult dicts
    count: int


class IngestResponse(BaseModel):
    """Ingestion response model."""
    documents_processed: int
    chunks_created: int
    errors: List[List[str]] = []


class AgentRequest(BaseModel):
    """Agent query request."""
    query: str = Field(..., description="Query for the conversational agent")
    state: Optional[Dict[str, Any]] = Field(default=None, description="Optional state for the agent")


class AgentResponse(BaseModel):
    """Agent query response."""
    query: str
    response: str
    state: Optional[Dict[str, Any]] = None

