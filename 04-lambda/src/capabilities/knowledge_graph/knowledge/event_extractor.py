"""Event extraction tool for extracting event information from web content."""

import logging
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExtractedEvent(BaseModel):
    """Extracted event information."""

    title: str = Field(..., description="Event title")
    date: str | None = Field(None, description="Event date")
    time: str | None = Field(None, description="Event time")
    location: str | None = Field(None, description="Event location")
    instructor: str | None = Field(None, description="Event instructor/teacher")
    description: str | None = Field(None, description="Event description")
    url: str | None = Field(None, description="Source URL")
    source: str = Field("web_crawl", description="Source of the event")


class EventExtractor:
    """Tool for extracting event information from web content."""

    def __init__(self, use_llm: bool = False):
        """
        Initialize event extractor.

        Args:
            use_llm: If True, use LLM for extraction (more accurate but slower)
        """
        self.use_llm = use_llm

    def extract_events_from_content(
        self, content: str, url: str | None = None
    ) -> list[ExtractedEvent]:
        """
        Extract event information from content.

        Args:
            content: Web content (HTML, markdown, or plain text)
            url: Source URL (optional)

        Returns:
            List of extracted events
        """
        if self.use_llm:
            return self._extract_with_llm(content, url)
        return self._extract_with_regex(content, url)

    def _extract_with_regex(self, content: str, url: str | None = None) -> list[ExtractedEvent]:
        """Extract events using regex patterns (simplified extraction)."""
        events = []

        # Look for common event patterns
        title_match = re.search(
            r"(?:title|event|class|workshop|seminar):\s*([^\n]+)", content, re.IGNORECASE
        )
        date_match = re.search(r"(?:date|when|on):\s*([^\n]+)", content, re.IGNORECASE)
        time_match = re.search(r"(?:time|starts?|begins?):\s*([^\n]+)", content, re.IGNORECASE)
        location_match = re.search(
            r"(?:location|venue|where|address):\s*([^\n]+)", content, re.IGNORECASE
        )
        instructor_match = re.search(
            r"(?:instructor|teacher|taught by|with|led by):\s*([^\n]+)", content, re.IGNORECASE
        )
        description_match = re.search(
            r"(?:description|details|about):\s*([^\n]+(?:\n[^\n]+){0,3})", content, re.IGNORECASE
        )

        # Only create event if we have at least title or date/time
        if title_match or date_match or time_match:
            event = ExtractedEvent(
                title=title_match.group(1).strip() if title_match else "Untitled Event",
                date=date_match.group(1).strip() if date_match else None,
                time=time_match.group(1).strip() if time_match else None,
                location=location_match.group(1).strip() if location_match else None,
                instructor=instructor_match.group(1).strip() if instructor_match else None,
                description=description_match.group(1).strip() if description_match else None,
                url=url,
                source="web_crawl",
            )
            events.append(event)

        return events

    def _extract_with_llm(self, content: str, url: str | None = None) -> list[ExtractedEvent]:
        """Extract events using LLM (more accurate but slower)."""
        # TODO: Implement LLM-based extraction with structured output
        # For now, fall back to regex
        logger.warning("LLM-based extraction not yet implemented, using regex")
        return self._extract_with_regex(content, url)

    def extract_events_from_crawled_pages(
        self, crawled_pages: list[dict[str, Any]]
    ) -> list[ExtractedEvent]:
        """
        Extract events from multiple crawled pages.

        Args:
            crawled_pages: List of crawled page dictionaries with 'content' and 'url' keys

        Returns:
            List of extracted events
        """
        all_events = []

        for page in crawled_pages:
            content = page.get("content_markdown") or page.get("content", "")
            url = page.get("url", "")

            events = self.extract_events_from_content(content, url)
            all_events.extend(events)

        return all_events

    def format_event_for_calendar(self, event: ExtractedEvent) -> dict[str, Any]:
        """
        Format extracted event for calendar creation.

        Args:
            event: Extracted event

        Returns:
            Dictionary formatted for calendar API
        """
        # Try to parse date and time into ISO format
        start_datetime = None
        end_datetime = None

        if event.date and event.time:
            try:
                # Simple parsing - in production, use dateutil or similar
                date_str = f"{event.date} {event.time}"
                # Try common formats
                for fmt in [
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d %I:%M %p",
                    "%B %d, %Y %H:%M",
                    "%B %d, %Y %I:%M %p",
                ]:
                    try:
                        start_datetime = datetime.strptime(date_str, fmt)
                        # Default to 1 hour duration if no end time
                        end_datetime = start_datetime.replace(hour=start_datetime.hour + 1)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                logger.warning(f"Failed to parse date/time: {e}")

        # Build description
        description_parts = []
        if event.description:
            description_parts.append(event.description)
        if event.instructor:
            description_parts.append(f"Instructor: {event.instructor}")
        if event.url:
            description_parts.append(f"Source: {event.url}")

        return {
            "summary": event.title,
            "description": "\n".join(description_parts) if description_parts else "",
            "location": event.location or "",
            "start": start_datetime.isoformat() if start_datetime else None,
            "end": end_datetime.isoformat() if end_datetime else None,
            "timezone": "America/Los_Angeles",  # Default timezone
        }
