"""Models for Knowledge extraction."""

from typing import Any

from pydantic import BaseModel, Field


class ExtractEventsRequest(BaseModel):
    """Request to extract events from text content."""

    content: str = Field(..., description="Text content to extract events from")
    url: str | None = Field(None, description="Source URL")
    use_llm: bool = Field(False, description="Whether to use LLM for extraction")


class ExtractEventsFromCrawledRequest(BaseModel):
    """Request to extract events from a crawled URL."""

    url: str = Field(..., description="URL to crawl and extract events from")
    use_llm: bool = Field(False, description="Whether to use LLM for extraction")


class ExtractedEventResponse(BaseModel):
    """Response containing extracted event."""

    title: str = Field(..., description="Event title")
    date: str | None = Field(None, description="Event date")
    time: str | None = Field(None, description="Event time")
    location: str | None = Field(None, description="Event location")
    instructor: str | None = Field(None, description="Event instructor/teacher")
    description: str | None = Field(None, description="Event description")
    url: str | None = Field(None, description="Source URL")
    source: str = Field("web_crawl", description="Source of the event")


class ExtractEventsResponse(BaseModel):
    """Response containing list of extracted events."""

    events: list[ExtractedEventResponse] = Field(default_factory=list)
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ExtractEventsFromCrawledRequest",
    "ExtractEventsRequest",
    "ExtractEventsResponse",
    "ExtractedEventResponse",
]
