"""Knowledge project REST API for event extraction."""

from fastapi import APIRouter, HTTPException
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from server.projects.knowledge.event_extractor import EventExtractor, ExtractedEvent

router = APIRouter()
logger = logging.getLogger(__name__)


class ExtractEventsRequest(BaseModel):
    """Request to extract events from content."""
    content: str = Field(..., description="Web content (HTML, markdown, or plain text)")
    url: Optional[str] = Field(None, description="Source URL")
    use_llm: bool = Field(False, description="Use LLM for extraction (more accurate but slower)")


class ExtractEventsResponse(BaseModel):
    """Response from event extraction."""
    success: bool = Field(..., description="Whether extraction was successful")
    events: List[ExtractedEvent] = Field(default_factory=list, description="List of extracted events")
    count: int = Field(0, description="Number of events extracted")


class ExtractEventsFromCrawledRequest(BaseModel):
    """Request to extract events from crawled pages."""
    crawled_pages: List[dict] = Field(..., description="List of crawled page dictionaries")
    use_llm: bool = Field(False, description="Use LLM for extraction")


@router.post("/extract-events", response_model=ExtractEventsResponse)
async def extract_events_endpoint(request: ExtractEventsRequest):
    """
    Extract event information from web content.
    
    This endpoint extracts event details (title, date, time, location, instructor)
    from web content using regex patterns or LLM-based extraction.
    
    **Use Cases:**
    - Extract events from crawled web pages
    - Parse event information from HTML content
    - Prepare events for calendar sync
    
    **Request Body:**
    ```json
    {
        "content": "Event: Team Meeting\nDate: 2024-01-15\nTime: 10:00 AM\nLocation: Conference Room A",
        "url": "https://example.com/events",
        "use_llm": false
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "events": [
            {
                "title": "Team Meeting",
                "date": "2024-01-15",
                "time": "10:00 AM",
                "location": "Conference Room A",
                "instructor": null,
                "description": null,
                "url": "https://example.com/events",
                "source": "web_crawl"
            }
        ],
        "count": 1
    }
    ```
    """
    try:
        extractor = EventExtractor(use_llm=request.use_llm)
        events = extractor.extract_events_from_content(
            content=request.content,
            url=request.url
        )
        
        return ExtractEventsResponse(
            success=True,
            events=events,
            count=len(events)
        )
    except Exception as e:
        logger.exception(f"Error extracting events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract events: {str(e)}")


@router.post("/extract-events-from-crawled", response_model=ExtractEventsResponse)
async def extract_events_from_crawled_endpoint(request: ExtractEventsFromCrawledRequest):
    """
    Extract events from multiple crawled pages.
    
    This endpoint processes multiple crawled pages and extracts event information
    from each one.
    
    **Request Body:**
    ```json
    {
        "crawled_pages": [
            {
                "content_markdown": "Event: Workshop\nDate: 2024-01-20",
                "url": "https://example.com/workshop"
            }
        ],
        "use_llm": false
    }
    ```
    """
    try:
        extractor = EventExtractor(use_llm=request.use_llm)
        events = extractor.extract_events_from_crawled_pages(request.crawled_pages)
        
        return ExtractEventsResponse(
            success=True,
            events=events,
            count=len(events)
        )
    except Exception as e:
        logger.exception(f"Error extracting events from crawled pages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract events: {str(e)}")
