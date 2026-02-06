"""Shared data models used across capabilities and workflows."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    """Status of an ingestion operation."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionOptions(BaseModel):
    """Options for content ingestion."""

    # Embedding configuration
    generate_embeddings: bool = Field(
        True, description="Whether to generate embeddings for the content"
    )
    embedding_model: str | None = Field(
        None, description="Embedding model to use (defaults to global setting)"
    )

    # Chunking configuration
    chunk_size: int = Field(1000, description="Maximum chunk size in characters")
    chunk_overlap: int = Field(200, description="Overlap between chunks in characters")

    # Processing options
    extract_metadata: bool = Field(True, description="Extract metadata from content")
    detect_language: bool = Field(True, description="Detect content language")
    
    # Storage options
    user_id: str | None = Field(None, description="User ID for data isolation")
    user_email: str | None = Field(None, description="User email for data isolation")
    tags: list[str] = Field(default_factory=list, description="Tags to associate with content")
    
    # Source information
    source_url: str | None = Field(None, description="Source URL of the content")
    source_type: str | None = Field(None, description="Type of source (web, file, etc.)")


class ScrapedContent(BaseModel):
    """Scraped content from a web page or document."""

    url: str = Field(..., description="Source URL")
    title: str | None = Field(None, description="Page/document title")
    content: str = Field(..., description="Extracted text content")
    html: str | None = Field(None, description="Raw HTML (if applicable)")
    markdown: str | None = Field(None, description="Markdown representation")
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: str | None = Field(None, description="Scrape timestamp")
    language: str | None = Field(None, description="Detected language")
    
    # Media
    images: list[str] = Field(default_factory=list, description="Extracted image URLs")
    links: list[str] = Field(default_factory=list, description="Extracted links")


class ChapterInfo(BaseModel):
    """Chapter/section information from media content."""

    title: str = Field(..., description="Chapter title")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float | None = Field(None, description="End time in seconds")
    description: str | None = Field(None, description="Chapter description")
    thumbnail: str | None = Field(None, description="Chapter thumbnail URL")


class MediaMetadata(BaseModel):
    """Metadata for media content (video, audio, etc.)."""

    title: str = Field(..., description="Media title")
    description: str | None = Field(None, description="Media description")
    duration: float | None = Field(None, description="Duration in seconds")
    author: str | None = Field(None, description="Content creator")
    upload_date: str | None = Field(None, description="Upload/publish date")
    
    # Chapters
    chapters: list[ChapterInfo] = Field(default_factory=list, description="Chapter information")
    
    # Additional metadata
    tags: list[str] = Field(default_factory=list, description="Content tags")
    categories: list[str] = Field(default_factory=list, description="Content categories")
    thumbnail: str | None = Field(None, description="Thumbnail URL")
    view_count: int | None = Field(None, description="View count")
    like_count: int | None = Field(None, description="Like count")


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""

    success: bool = Field(..., description="Whether ingestion succeeded")
    document_id: str | None = Field(None, description="ID of ingested document")
    chunk_count: int = Field(0, description="Number of chunks created")
    error: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional result metadata")
