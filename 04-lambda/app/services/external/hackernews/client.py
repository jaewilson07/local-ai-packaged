"""Hacker News API client.

Hacker News provides a free, no-authentication-required API via Firebase.
This client supports both the official Firebase API and the Algolia search API.

Firebase API: https://hacker-news.firebaseio.com/v0/
Algolia Search: https://hn.algolia.com/api/v1/

The Algolia API is preferred for search as it provides full-text search
capabilities, while the Firebase API is used for fetching specific items
or browsing top/new/best stories.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# API endpoints
HN_FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA_BASE = "https://hn.algolia.com/api/v1"

StoryType = Literal["top", "new", "best", "ask", "show", "job"]


@dataclass
class HNStory:
    """Hacker News story/post data."""

    id: int
    title: str
    url: str | None = None
    text: str | None = None  # For self-posts (Ask HN, etc.)
    author: str = ""
    score: int = 0
    num_comments: int = 0
    created_at: datetime | None = None
    story_type: str = "story"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url or f"https://news.ycombinator.com/item?id={self.id}",
            "text": self.text,
            "author": self.author,
            "score": self.score,
            "num_comments": self.num_comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "story_type": self.story_type,
            "tags": self.tags,
            "source": "hackernews",
        }

    @property
    def hn_url(self) -> str:
        """Get the Hacker News discussion URL."""
        return f"https://news.ycombinator.com/item?id={self.id}"

    @property
    def content_url(self) -> str:
        """Get the content URL (external link or HN discussion for self-posts)."""
        return self.url or self.hn_url


class HackerNewsClient:
    """Async client for Hacker News API."""

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the Hacker News client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HackerNewsClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        tags: str | None = None,
        num_results: int = 20,
        sort_by: Literal["relevance", "date"] = "relevance",
    ) -> list[HNStory]:
        """
        Search Hacker News using the Algolia API.

        This is the primary search method as it provides full-text search.

        Args:
            query: Search query string
            tags: Filter by tags (e.g., "story", "ask_hn", "show_hn", "front_page")
            num_results: Maximum number of results to return
            sort_by: Sort by relevance or date

        Returns:
            List of HNStory objects matching the query
        """
        endpoint = "search" if sort_by == "relevance" else "search_by_date"
        url = f"{HN_ALGOLIA_BASE}/{endpoint}"

        params = {
            "query": query,
            "hitsPerPage": min(num_results, 50),  # Algolia max is 1000, but limit for performance
        }

        if tags:
            params["tags"] = tags

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            stories = []
            for hit in data.get("hits", []):
                story = self._parse_algolia_hit(hit)
                if story:
                    stories.append(story)

            logger.info(f"hackernews_search: query='{query}', results={len(stories)}")
            return stories

        except httpx.HTTPStatusError as e:
            logger.error(f"hackernews_search_error: HTTP {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"hackernews_search_error: {e}")
            raise

    async def get_stories(
        self,
        story_type: StoryType = "top",
        limit: int = 30,
    ) -> list[HNStory]:
        """
        Get stories by type using the Firebase API.

        Args:
            story_type: Type of stories to fetch (top, new, best, ask, show, job)
            limit: Maximum number of stories to return

        Returns:
            List of HNStory objects
        """
        # Get story IDs
        url = f"{HN_FIREBASE_BASE}/{story_type}stories.json"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            story_ids = response.json()[:limit]

            # Fetch story details in parallel (batch of 10 at a time)
            stories = []
            for i in range(0, len(story_ids), 10):
                batch = story_ids[i : i + 10]
                batch_stories = await asyncio.gather(
                    *[self.get_item(sid) for sid in batch],
                    return_exceptions=True,
                )
                for story in batch_stories:
                    if isinstance(story, HNStory):
                        stories.append(story)

            logger.info(f"hackernews_get_stories: type={story_type}, count={len(stories)}")
            return stories

        except Exception as e:
            logger.exception(f"hackernews_get_stories_error: {e}")
            raise

    async def get_item(self, item_id: int) -> HNStory | None:
        """
        Get a single item (story, comment, etc.) by ID.

        Args:
            item_id: Hacker News item ID

        Returns:
            HNStory object or None if not found/invalid
        """
        url = f"{HN_FIREBASE_BASE}/item/{item_id}.json"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            if not data or data.get("type") not in ("story", "job", "poll"):
                return None

            return HNStory(
                id=data.get("id"),
                title=data.get("title", ""),
                url=data.get("url"),
                text=data.get("text"),
                author=data.get("by", ""),
                score=data.get("score", 0),
                num_comments=data.get("descendants", 0),
                created_at=datetime.fromtimestamp(data["time"]) if data.get("time") else None,
                story_type=data.get("type", "story"),
            )

        except Exception as e:
            logger.warning(f"hackernews_get_item_error: id={item_id}, error={e}")
            return None

    def _parse_algolia_hit(self, hit: dict) -> HNStory | None:
        """Parse an Algolia search hit into an HNStory."""
        try:
            # Algolia returns slightly different field names
            created_at = None
            if hit.get("created_at_i"):
                created_at = datetime.fromtimestamp(hit["created_at_i"])

            return HNStory(
                id=int(hit.get("objectID", 0)),
                title=hit.get("title") or hit.get("story_title", ""),
                url=hit.get("url"),
                text=hit.get("story_text"),
                author=hit.get("author", ""),
                score=hit.get("points", 0),
                num_comments=hit.get("num_comments", 0),
                created_at=created_at,
                story_type=hit.get("_tags", ["story"])[0] if hit.get("_tags") else "story",
                tags=hit.get("_tags", []),
            )
        except Exception as e:
            logger.warning(f"hackernews_parse_error: {e}")
            return None


async def search_hackernews(
    query: str,
    num_results: int = 20,
    story_type: StoryType | None = None,
    sort_by: Literal["relevance", "date"] = "relevance",
) -> list[dict]:
    """
    Convenience function to search Hacker News.

    Args:
        query: Search query string
        num_results: Maximum number of results
        story_type: Optional filter by story type (for browsing, not search)
        sort_by: Sort by relevance or date

    Returns:
        List of story dictionaries
    """
    async with HackerNewsClient() as client:
        if story_type and not query:
            # Browse by story type
            stories = await client.get_stories(story_type, limit=num_results)
        else:
            # Search using Algolia
            tags = None
            if story_type == "ask":
                tags = "ask_hn"
            elif story_type == "show":
                tags = "show_hn"
            elif story_type:
                tags = story_type

            stories = await client.search(
                query=query,
                tags=tags,
                num_results=num_results,
                sort_by=sort_by,
            )

        return [s.to_dict() for s in stories]
