"""Pydantic models for Knowledge project operations."""

from typing import Any

from capabilities.knowledge_graph.knowledge.event_extractor import ExtractedEvent
from pydantic import BaseModel, Field


class ExtractEventsRequest(BaseModel):
    """Request to extract events from content."""

    content: str = Field(..., description="Web content (HTML, markdown, or plain text)")
    url: str | None = Field(None, description="Source URL")
    use_llm: bool | None = Field(None, description="Use LLM for extraction (overrides default)")


class ExtractEventsResponse(BaseModel):
    """Response from event extraction."""

    success: bool = Field(..., description="Whether extraction was successful")
    events: list[ExtractedEvent] = Field(
        default_factory=list, description="List of extracted events"
    )
    count: int = Field(0, description="Number of events extracted")


class ExtractEventsFromCrawledRequest(BaseModel):
    """Request to extract events from crawled pages."""

    crawled_pages: list[dict[str, Any]] = Field(
        ..., description="List of crawled page dictionaries"
    )
    use_llm: bool | None = Field(None, description="Use LLM for extraction (overrides default)")


class ExtractEventsFromCrawledResponse(BaseModel):
    """Response from event extraction from crawled pages."""

    success: bool = Field(..., description="Whether extraction was successful")
    events: list[ExtractedEvent] = Field(
        default_factory=list, description="List of extracted events"
    )
    count: int = Field(0, description="Number of events extracted")
