"""Data models for Knowledge Base project."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    """Status of an article edit proposal."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class SourceType(str, Enum):
    """Source type for articles."""

    CIRCLE_SO = "circle_so"
    DEV_TO = "dev_to"
    REDDIT = "reddit"
    GDRIVE = "gdrive"
    MANUAL = "manual"
    WEB_CRAWL = "web_crawl"
    IMPORT = "import"


class ArticleVersion(BaseModel):
    """A historical version of an article."""

    version: int
    content: str
    changed_at: datetime
    changed_by: str
    change_reason: str | None = None


class Article(BaseModel):
    """Knowledge Base article model."""

    id: str | None = Field(None, alias="_id")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Markdown content")
    content_embedding: list[float] | None = Field(None, description="Vector embedding for RAG")
    author_email: str = Field(..., description="Owner email")
    source_url: str | None = Field(None, description="Original source URL")
    source_type: SourceType = Field(default=SourceType.MANUAL)
    tags: list[str] = Field(default_factory=list)
    version: int = Field(default=1)
    version_history: list[ArticleVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    reliability_score: float | None = Field(None, ge=0.0, le=1.0)
    last_verified_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ArticleEditProposal(BaseModel):
    """Proposal to edit an article."""

    id: str | None = Field(None, alias="_id")
    article_id: str = Field(..., description="ID of article to edit")
    article_slug: str | None = Field(None, description="Slug of article for reference")
    article_title: str | None = Field(None, description="Title of article for reference")
    proposer_email: str = Field(..., description="Email of person proposing edit")
    original_content: str = Field(..., description="Original article content")
    proposed_content: str = Field(..., description="Proposed new content")
    change_reason: str = Field(..., description="Reason for the change")
    supporting_sources: list[str] = Field(default_factory=list)
    status: ProposalStatus = Field(default=ProposalStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None
    reviewer_email: str | None = None
    reviewer_notes: str | None = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# Request/Response models for API


class ArticleCreateRequest(BaseModel):
    """Request to create a new article."""

    title: str
    content: str
    slug: str | None = None
    source_url: str | None = None
    source_type: SourceType = SourceType.MANUAL
    tags: list[str] = Field(default_factory=list)


class ArticleUpdateRequest(BaseModel):
    """Request to update an article."""

    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    change_reason: str | None = None


class ProposalCreateRequest(BaseModel):
    """Request to create an edit proposal."""

    article_id: str
    original_content: str
    proposed_content: str
    change_reason: str
    supporting_sources: list[str] = Field(default_factory=list)


class ProposalReviewRequest(BaseModel):
    """Request to review a proposal."""

    action: str = Field(..., pattern="^(approve|reject|request_changes)$")
    reviewer_notes: str | None = None


class ChatQueryRequest(BaseModel):
    """Request for chat query with RAG context."""

    query: str
    rag_results: list[dict[str, Any]] = Field(default_factory=list)
    web_results: list[dict[str, Any]] = Field(default_factory=list)


class ChatQueryResponse(BaseModel):
    """Response from chat query."""

    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)


class FetchUrlRequest(BaseModel):
    """Request to fetch URL content."""

    url: str


class ArticleListResponse(BaseModel):
    """Response for article list."""

    articles: list[Article]
    total: int
    page: int
    per_page: int


class ArticleSearchRequest(BaseModel):
    """Request for article search."""

    query: str
    match_count: int = Field(default=10, ge=1, le=50)
