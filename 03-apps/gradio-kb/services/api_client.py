"""API client for Lambda Knowledge Base endpoints."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class KnowledgeBaseClient:
    """Client for interacting with Lambda Knowledge Base API."""

    def __init__(
        self,
        base_url: str = "http://lambda-server:8000",
        timeout: float = 60.0,
    ):
        """
        Initialize the Knowledge Base API client.

        Args:
            base_url: Lambda server base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def chat_query(
        self,
        query: str,
        include_web_search: bool = True,
    ) -> dict[str, Any]:
        """
        Send a chat query and get RAG-enhanced response with citations.

        Args:
            query: User question
            include_web_search: Whether to include web search results

        Returns:
            Dict with 'answer' and 'citations' keys
        """
        client = await self._get_client()

        try:
            # First, search the RAG knowledge base
            rag_response = await client.post(
                "/api/v1/rag/search",
                json={
                    "query": query,
                    "match_count": 5,
                    "search_type": "hybrid",
                },
            )
            rag_response.raise_for_status()
            rag_results = rag_response.json()

            # Optionally search the web
            web_results = {"results": []}
            if include_web_search:
                try:
                    web_response = await client.post(
                        "/api/v1/searxng/search",
                        json={
                            "query": query,
                            "result_count": 5,
                        },
                    )
                    web_response.raise_for_status()
                    web_results = web_response.json()
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")

            # Get agent response with combined context
            agent_response = await client.post(
                "/api/v1/kb/chat",
                json={
                    "query": query,
                    "rag_results": rag_results.get("results", []),
                    "web_results": web_results.get("results", []),
                },
            )
            agent_response.raise_for_status()
            return agent_response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise

    async def get_article(self, article_id: str) -> dict[str, Any]:
        """
        Fetch an article by ID.

        Args:
            article_id: MongoDB document ID

        Returns:
            Article data dict
        """
        client = await self._get_client()

        response = await client.get(f"/api/v1/kb/articles/{article_id}")
        response.raise_for_status()
        return response.json()

    async def fetch_url_content(self, url: str) -> dict[str, Any]:
        """
        Fetch and parse content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Parsed content dict with title, content, etc.
        """
        client = await self._get_client()

        response = await client.post(
            "/api/v1/kb/fetch-url",
            json={"url": url},
        )
        response.raise_for_status()
        return response.json()

    async def list_articles(
        self,
        page: int = 1,
        per_page: int = 20,
        source_type: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        List articles with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            source_type: Filter by source type
            tags: Filter by tags

        Returns:
            Dict with 'articles', 'total', 'page', 'per_page'
        """
        client = await self._get_client()

        params = {"page": page, "per_page": per_page}
        if source_type:
            params["source_type"] = source_type
        if tags:
            params["tags"] = ",".join(tags)

        response = await client.get("/api/v1/kb/articles", params=params)
        response.raise_for_status()
        return response.json()

    async def submit_proposal(
        self,
        article_id: str,
        original_content: str,
        proposed_content: str,
        change_reason: str,
        supporting_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Submit an article edit proposal.

        Args:
            article_id: ID of the article to edit
            original_content: Original article content
            proposed_content: Proposed new content
            change_reason: Reason for the change
            supporting_sources: List of supporting URLs

        Returns:
            Dict with 'success' and proposal ID or error
        """
        client = await self._get_client()

        response = await client.post(
            "/api/v1/kb/proposals",
            json={
                "article_id": article_id,
                "original_content": original_content,
                "proposed_content": proposed_content,
                "change_reason": change_reason,
                "supporting_sources": supporting_sources or [],
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_my_proposals(self, status: str | None = None) -> dict[str, Any]:
        """
        Get proposals submitted by the current user.

        Args:
            status: Filter by status (pending, approved, rejected)

        Returns:
            List of proposals
        """
        client = await self._get_client()

        params = {}
        if status:
            params["status"] = status

        response = await client.get("/api/v1/kb/proposals/mine", params=params)
        response.raise_for_status()
        return response.json()

    async def get_proposals_for_review(self) -> dict[str, Any]:
        """
        Get proposals pending review for articles owned by current user.

        Returns:
            List of proposals to review
        """
        client = await self._get_client()

        response = await client.get("/api/v1/kb/proposals/review")
        response.raise_for_status()
        return response.json()

    async def review_proposal(
        self,
        proposal_id: str,
        action: str,
        reviewer_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Review a proposal (approve/reject).

        Args:
            proposal_id: ID of the proposal
            action: 'approve', 'reject', or 'request_changes'
            reviewer_notes: Optional notes for the proposer

        Returns:
            Result of the review action
        """
        client = await self._get_client()

        response = await client.post(
            f"/api/v1/kb/proposals/{proposal_id}/review",
            json={
                "action": action,
                "reviewer_notes": reviewer_notes,
            },
        )
        response.raise_for_status()
        return response.json()

    async def search_articles(
        self,
        query: str,
        match_count: int = 10,
    ) -> dict[str, Any]:
        """
        Search articles by content.

        Args:
            query: Search query
            match_count: Number of results

        Returns:
            Search results
        """
        client = await self._get_client()

        response = await client.post(
            "/api/v1/kb/search",
            json={
                "query": query,
                "match_count": match_count,
            },
        )
        response.raise_for_status()
        return response.json()
