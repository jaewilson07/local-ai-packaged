"""Dev.to (Forem) API client.

Dev.to provides a free public API for accessing articles and content.
No API key is required for read operations.

API Documentation: https://developers.forem.com/api/v1

Note: Dev.to is built on the Forem platform, so this client could
potentially work with other Forem-based communities with minor modifications.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# API endpoint
DEVTO_API_BASE = "https://dev.to/api"


@dataclass
class DevToArticle:
    """Dev.to article data."""

    id: int
    title: str
    description: str
    url: str
    cover_image: str | None = None
    published_at: datetime | None = None
    reading_time_minutes: int = 0
    tags: list[str] = field(default_factory=list)
    author_username: str = ""
    author_name: str = ""
    reactions_count: int = 0
    comments_count: int = 0
    body_markdown: str | None = None  # Only available when fetching single article

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "cover_image": self.cover_image,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "reading_time_minutes": self.reading_time_minutes,
            "tags": self.tags,
            "author_username": self.author_username,
            "author_name": self.author_name,
            "reactions_count": self.reactions_count,
            "comments_count": self.comments_count,
            "source": "devto",
        }

    @property
    def content_preview(self) -> str:
        """Get a content preview from description or body."""
        if self.body_markdown:
            return (
                self.body_markdown[:500] + "..."
                if len(self.body_markdown) > 500
                else self.body_markdown
            )
        return self.description


class DevToClient:
    """Async client for Dev.to API."""

    def __init__(self, timeout: float = 30.0, api_key: str | None = None):
        """
        Initialize the Dev.to client.

        Args:
            timeout: Request timeout in seconds
            api_key: Optional API key for authenticated requests
                    (not required for public read operations)
        """
        self.timeout = timeout
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DevToClient":
        """Async context manager entry."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
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
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["api-key"] = self.api_key
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_articles(
        self,
        query: str | None = None,
        tag: str | None = None,
        tags: list[str] | None = None,
        username: str | None = None,
        state: Literal["fresh", "rising", "all"] = "all",
        top: int | None = None,  # Time period in days for top articles
        per_page: int = 30,
        page: int = 1,
    ) -> list[DevToArticle]:
        """
        Search for articles on Dev.to.

        The Dev.to API doesn't have a direct search endpoint, but we can filter
        by tags, username, and state. For text search, use the tag parameter
        or fetch articles and filter client-side.

        Args:
            query: Text query for client-side filtering (optional)
            tag: Filter by single tag (e.g., "python", "ai", "machinelearning")
            tags: Filter by multiple tags (comma-separated in API)
            username: Filter by author username
            state: Article state filter (fresh=recent, rising=trending, all=any)
            top: Time period for top articles (e.g., 7 for past week)
            per_page: Results per page (max 1000, recommended 30)
            page: Page number for pagination

        Returns:
            List of DevToArticle objects
        """
        url = f"{DEVTO_API_BASE}/articles"

        params = {
            "per_page": min(per_page, 100),  # Reasonable limit
            "page": page,
        }

        if tag:
            params["tag"] = tag.lower()
        elif tags:
            params["tags"] = ",".join(t.lower() for t in tags)

        if username:
            params["username"] = username

        if state != "all":
            params["state"] = state

        if top:
            params["top"] = top

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data:
                article = self._parse_article(item)
                if article:
                    # Apply query filter if provided
                    if query:
                        query_lower = query.lower()
                        if (
                            query_lower not in article.title.lower()
                            and query_lower not in article.description.lower()
                            and not any(query_lower in tag.lower() for tag in article.tags)
                        ):
                            continue
                    articles.append(article)

            logger.info(f"devto_search: tag={tag}, query={query}, results={len(articles)}")
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"devto_search_error: HTTP {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"devto_search_error: {e}")
            raise

    async def get_article(self, article_id: int) -> DevToArticle | None:
        """
        Get a single article by ID (includes full body content).

        Args:
            article_id: Dev.to article ID

        Returns:
            DevToArticle with full content or None if not found
        """
        url = f"{DEVTO_API_BASE}/articles/{article_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            article = self._parse_article(data)
            if article:
                article.body_markdown = data.get("body_markdown")

            return article

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"devto_get_article_error: HTTP {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"devto_get_article_error: {e}")
            raise

    async def get_article_by_path(self, username: str, slug: str) -> DevToArticle | None:
        """
        Get a single article by username and slug.

        Args:
            username: Author username
            slug: Article slug

        Returns:
            DevToArticle with full content or None if not found
        """
        url = f"{DEVTO_API_BASE}/articles/{username}/{slug}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            article = self._parse_article(data)
            if article:
                article.body_markdown = data.get("body_markdown")

            return article

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"devto_get_article_by_path_error: HTTP {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"devto_get_article_by_path_error: {e}")
            raise

    async def get_latest_articles(
        self,
        per_page: int = 30,
        page: int = 1,
    ) -> list[DevToArticle]:
        """
        Get the latest published articles.

        Args:
            per_page: Results per page
            page: Page number

        Returns:
            List of latest DevToArticle objects
        """
        return await self.search_articles(state="fresh", per_page=per_page, page=page)

    async def get_top_articles(
        self,
        days: int = 7,
        per_page: int = 30,
    ) -> list[DevToArticle]:
        """
        Get top articles from the past N days.

        Args:
            days: Number of days to look back
            per_page: Results per page

        Returns:
            List of top DevToArticle objects
        """
        return await self.search_articles(top=days, per_page=per_page)

    def _parse_article(self, data: dict) -> DevToArticle | None:
        """Parse API response into DevToArticle."""
        try:
            published_at = None
            if data.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        data["published_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # Parse tags - can be list or comma-separated string
            tags = data.get("tag_list", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            return DevToArticle(
                id=data.get("id"),
                title=data.get("title", ""),
                description=data.get("description", ""),
                url=data.get("url", ""),
                cover_image=data.get("cover_image"),
                published_at=published_at,
                reading_time_minutes=data.get("reading_time_minutes", 0),
                tags=tags,
                author_username=data.get("user", {}).get("username", ""),
                author_name=data.get("user", {}).get("name", ""),
                reactions_count=data.get("positive_reactions_count", 0),
                comments_count=data.get("comments_count", 0),
            )
        except Exception as e:
            logger.warning(f"devto_parse_error: {e}")
            return None


async def search_devto(
    query: str | None = None,
    tag: str | None = None,
    tags: list[str] | None = None,
    num_results: int = 30,
    top_days: int | None = None,
) -> list[dict]:
    """
    Convenience function to search Dev.to articles.

    Args:
        query: Text query for filtering results
        tag: Filter by single tag (e.g., "python", "ai")
        tags: Filter by multiple tags
        num_results: Maximum number of results
        top_days: If set, get top articles from past N days

    Returns:
        List of article dictionaries
    """
    async with DevToClient() as client:
        if top_days:
            articles = await client.get_top_articles(days=top_days, per_page=num_results)
            # Apply query filter if provided
            if query:
                query_lower = query.lower()
                articles = [
                    a
                    for a in articles
                    if query_lower in a.title.lower()
                    or query_lower in a.description.lower()
                    or any(query_lower in t.lower() for t in a.tags)
                ]
        else:
            articles = await client.search_articles(
                query=query,
                tag=tag,
                tags=tags,
                per_page=num_results,
            )

        return [a.to_dict() for a in articles]


# Common AI/ML/Programming tags on Dev.to
DEVTO_AI_TAGS = [
    "ai",
    "machinelearning",
    "deeplearning",
    "python",
    "datascience",
    "openai",
    "llm",
    "gpt",
    "chatgpt",
    "langchain",
    "huggingface",
    "transformers",
    "pytorch",
    "tensorflow",
    "stablediffusion",
    "generativeai",
]
