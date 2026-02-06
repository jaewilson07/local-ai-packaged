"""Deep research models.

This module provides data models for deep research tools including
the composite research_and_store tool for Cursor agent integration.
"""

from typing import Literal

from pydantic import BaseModel, Field

# ============================================================================
# Research and Store Tool Models
# ============================================================================


# Available research sources
RESEARCH_SOURCES = Literal[
    "youtube",
    "web",
    "reddit",
    "hackernews",
    "devto",
]

# Default sources for each focus type
DEFAULT_SOURCES_BY_FOCUS = {
    "videos": ["youtube"],
    "articles": ["web", "devto"],
    "communities": ["reddit", "hackernews", "devto"],
    "all": ["youtube", "web", "reddit", "hackernews", "devto"],
    "both": ["youtube", "web"],  # Legacy - same as videos + articles
}


class ResearchAndStoreRequest(BaseModel):
    """Request model for composite research and store operation."""

    query: str = Field(..., description="Research query/topic to investigate")
    focus: Literal["videos", "articles", "communities", "all", "both"] = Field(
        default="all",
        description="What type of content to search for: videos, articles, communities, all, or both (legacy)",
    )
    sources: list[str] | None = Field(
        default=None,
        description=(
            "Specific sources to search. Options: youtube, web, reddit, hackernews, devto. "
            "If not specified, uses default sources based on focus."
        ),
    )
    video_recency_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Only ingest videos published within this many days",
    )
    max_videos: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of videos to ingest",
    )
    max_articles: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of articles to ingest",
    )
    max_community_posts: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Maximum number of community posts (Reddit, HN, Dev.to) to ingest",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional tags to apply to ingested content",
    )
    project_scope: str | None = Field(
        default=None,
        description="Optional project scope for organizing research (e.g., 'comfyui-lora-research')",
    )
    extract_entities: bool = Field(
        default=False,
        description="Use LLM to extract entities from videos (slower but richer metadata)",
    )
    extract_topics: bool = Field(
        default=True,
        description="Use LLM to classify topics",
    )
    subreddits: list[str] | None = Field(
        default=None,
        description="Specific subreddits to search (e.g., ['LocalLLaMA', 'StableDiffusion'])",
    )

    def get_sources(self) -> list[str]:
        """Get the list of sources to search based on focus and explicit sources."""
        if self.sources:
            return self.sources
        return DEFAULT_SOURCES_BY_FOCUS.get(self.focus, ["youtube", "web"])


class IngestedItem(BaseModel):
    """Details about a single ingested item."""

    type: Literal["video", "article", "reddit", "hackernews", "devto"]
    url: str
    title: str
    document_id: str | None = None
    chunks_created: int = 0
    success: bool = True
    error: str | None = None
    published_date: str | None = None
    source: str | None = None  # Source identifier (reddit, hackernews, devto, youtube, web)
    author: str | None = None  # Author/username
    score: int | None = None  # Upvotes/reactions


class ResearchAndStoreResponse(BaseModel):
    """Response model for composite research and store operation."""

    success: bool
    query: str
    focus: str
    sources_searched: list[str] = Field(default_factory=list)
    items_found: int = 0
    items_ingested: int = 0
    videos_ingested: int = 0
    articles_ingested: int = 0
    community_posts_ingested: int = 0  # Reddit + HN + Dev.to
    reddit_ingested: int = 0
    hackernews_ingested: int = 0
    devto_ingested: int = 0
    total_chunks_created: int = 0
    ingested_items: list[IngestedItem] = Field(default_factory=list)
    skipped_items: list[IngestedItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    project_scope: str | None = None
    tags: list[str] | None = None


# ============================================================================
# Existing Deep Research Tool Models
# ============================================================================


class SearchWebRequest(BaseModel):
    """Request model for web search."""

    query: str
    engines: list[str] | None = None
    result_count: int = Field(default=5, ge=1, le=20)


class SearchWebResponse(BaseModel):
    """Response model for web search."""

    query: str
    results: list[dict]
    count: int
    success: bool = True


class FetchPageRequest(BaseModel):
    """Request model for page fetch."""

    url: str


class FetchPageResponse(BaseModel):
    """Response model for page fetch."""

    url: str
    content: str
    metadata: dict = Field(default_factory=dict)
    success: bool = True


class ParseDocumentRequest(BaseModel):
    """Request model for document parsing."""

    content: str
    content_type: Literal["html", "markdown", "text"] = "html"


class ParseDocumentResponse(BaseModel):
    """Response model for document parsing."""

    chunks: list[dict]
    metadata: dict = Field(default_factory=dict)
    success: bool = True


class DocumentChunk(BaseModel):
    """Model for a document chunk."""

    content: str
    index: int
    start_char: int = 0
    end_char: int = 0
    metadata: dict = Field(default_factory=dict)
    token_count: int = 0


class IngestKnowledgeRequest(BaseModel):
    """Request model for knowledge ingestion."""

    chunks: list[DocumentChunk]
    session_id: str
    source_url: str
    title: str | None = None


class IngestKnowledgeResponse(BaseModel):
    """Response model for knowledge ingestion."""

    document_id: str | None = None
    chunks_created: int = 0
    facts_added: int = 0
    success: bool = True
    errors: list[str] = Field(default_factory=list)


class QueryKnowledgeRequest(BaseModel):
    """Request model for knowledge query."""

    question: str
    session_id: str
    match_count: int = Field(default=5, ge=1, le=50)
    search_type: Literal["semantic", "text", "hybrid"] = "hybrid"


class QueryKnowledgeResponse(BaseModel):
    """Response model for knowledge query."""

    results: list[dict]
    count: int
    success: bool = True


__all__ = [
    "DEFAULT_SOURCES_BY_FOCUS",
    "DocumentChunk",
    "FetchPageRequest",
    "FetchPageResponse",
    "IngestKnowledgeRequest",
    "IngestKnowledgeResponse",
    "IngestedItem",
    "ParseDocumentRequest",
    "ParseDocumentResponse",
    "QueryKnowledgeRequest",
    "QueryKnowledgeResponse",
    "RESEARCH_SOURCES",
    "ResearchAndStoreRequest",
    "ResearchAndStoreResponse",
    "SearchWebRequest",
    "SearchWebResponse",
]
