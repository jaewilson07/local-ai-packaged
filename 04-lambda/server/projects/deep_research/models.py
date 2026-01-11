"""Pydantic models for Deep Research API."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class SearchResult(BaseModel):
    """Individual search result from web search."""

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet/content")
    engine: str | None = Field(None, description="Search engine that provided this result")
    score: float | None = Field(None, description="Relevance score")


class SearchWebRequest(BaseModel):
    """Request model for web search."""

    query: str = Field(..., description="Search query string")
    engines: list[str] | None = Field(None, description="Optional engine filters")
    result_count: int = Field(
        default=5, ge=1, le=20, description="Number of results to return (1-20)"
    )


class SearchWebResponse(BaseModel):
    """Response model for web search."""

    query: str = Field(..., description="The search query")
    results: list[SearchResult] = Field(default_factory=list, description="List of search results")
    count: int = Field(default=0, description="Number of results returned")
    success: bool = Field(..., description="Whether the search succeeded")


class FetchPageRequest(BaseModel):
    """Request model for fetching a page."""

    url: HttpUrl = Field(..., description="URL to fetch")


class FetchPageResponse(BaseModel):
    """Response model for fetching a page."""

    url: str = Field(..., description="The fetched URL")
    content: str = Field(..., description="Raw markdown/HTML content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Page metadata (title, description, etc.)"
    )
    success: bool = Field(..., description="Whether the fetch succeeded")


class DocumentChunk(BaseModel):
    """Structured document chunk."""

    content: str = Field(..., description="Chunk content")
    index: int = Field(..., description="Chunk index")
    start_char: int = Field(..., description="Start character position")
    end_char: int = Field(..., description="End character position")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    token_count: int | None = Field(None, description="Token count for this chunk")


class ParseDocumentRequest(BaseModel):
    """Request model for parsing a document."""

    content: str = Field(..., description="Raw content to parse")
    content_type: Literal["html", "markdown", "text"] = Field(
        default="html", description="Content type hint for parsing"
    )


class ParseDocumentResponse(BaseModel):
    """Response model for parsing a document."""

    chunks: list[DocumentChunk] = Field(default_factory=list, description="Structured chunks")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    success: bool = Field(..., description="Whether the parsing succeeded")


class IngestKnowledgeRequest(BaseModel):
    """Request model for ingesting knowledge into RAG and Graphiti."""

    chunks: list[DocumentChunk] = Field(..., description="Document chunks from parse_document")
    session_id: str = Field(..., description="Session ID for data isolation")
    source_url: str = Field(..., description="Source URL of the document")
    title: str | None = Field(None, description="Document title (optional)")


class IngestKnowledgeResponse(BaseModel):
    """Response model for knowledge ingestion."""

    document_id: str = Field(..., description="MongoDB document ID")
    chunks_created: int = Field(..., description="Number of chunks created")
    facts_added: int = Field(default=0, description="Number of facts added to Graphiti")
    success: bool = Field(..., description="Whether the ingestion succeeded")
    errors: list[str] = Field(default_factory=list, description="List of errors if any")


class CitedChunk(BaseModel):
    """A chunk with citation information."""

    chunk_id: str = Field(..., description="Chunk ID for citation")
    content: str = Field(..., description="Chunk content")
    document_id: str = Field(..., description="Document ID")
    document_source: str = Field(..., description="Document source URL")
    similarity: float = Field(..., description="Similarity/relevance score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class QueryKnowledgeRequest(BaseModel):
    """Request model for querying knowledge base."""

    question: str = Field(..., description="Question to search for")
    session_id: str = Field(..., description="Session ID to filter results")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    search_type: Literal["semantic", "text", "hybrid", "graph"] = Field(
        default="hybrid",
        description="Type of search to perform. 'graph' enables Phase 6 graph-enhanced reasoning.",
    )
    use_graphiti: bool = Field(
        default=False,
        description="Enable Graphiti graph traversal for multi-hop reasoning (Phase 6)",
    )


class QueryKnowledgeResponse(BaseModel):
    """Response model for knowledge query."""

    results: list[CitedChunk] = Field(default_factory=list, description="List of cited chunks")
    count: int = Field(default=0, description="Number of results returned")
    success: bool = Field(..., description="Whether the query succeeded")
