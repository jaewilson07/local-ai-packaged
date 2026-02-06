"""Knowledge project REST API for event extraction."""

import logging

from app.capabilities.knowledge_graph.knowledge.dependencies import KnowledgeDeps
from app.capabilities.knowledge_graph.knowledge.models import (
    ExtractEventsFromCrawledRequest,
    ExtractEventsFromCrawledResponse,
    ExtractEventsRequest,
    ExtractEventsResponse,
)
from app.capabilities.knowledge_graph.knowledge.tools import (
    extract_events_from_content,
    extract_events_from_crawled_pages,
)
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from pydantic_ai import RunContext

router = APIRouter()
logger = logging.getLogger(__name__)


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
    # Initialize dependencies
    deps = KnowledgeDeps.from_settings(use_llm=request.use_llm)
    await deps.initialize()

    try:
        # Create RunContext for tools
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        # Call underlying capability
        events = await extract_events_from_content(
            tool_ctx, content=request.content, url=request.url, use_llm=request.use_llm
        )

        return ExtractEventsResponse(success=True, events=events, count=len(events))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("event_extraction_error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to extract events: {e!s}") from e
    finally:
        await deps.cleanup()


@router.post("/extract-events-from-crawled", response_model=ExtractEventsFromCrawledResponse)
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
    # Initialize dependencies
    deps = KnowledgeDeps.from_settings(use_llm=request.use_llm)
    await deps.initialize()

    try:
        # Create RunContext for tools
        tool_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        # Call underlying capability
        events = await extract_events_from_crawled_pages(
            tool_ctx, crawled_pages=request.crawled_pages, use_llm=request.use_llm
        )

        return ExtractEventsFromCrawledResponse(success=True, events=events, count=len(events))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("event_extraction_from_crawled_error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to extract events: {e!s}") from e
    finally:
        await deps.cleanup()
