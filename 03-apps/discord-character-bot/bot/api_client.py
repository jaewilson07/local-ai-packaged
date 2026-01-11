"""HTTP client for Lambda API services."""

import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class APIClient:
    """Client for making HTTP requests to Lambda API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize API client.

        Args:
            base_url: Base URL for Lambda API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v1/discord/characters/add")
            json_data: Optional JSON data for request body

        Returns:
            Response JSON as dictionary

        Raises:
            aiohttp.ClientError: If request fails
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with session.request(method, url, json=json_data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise

    async def add_character(
        self, channel_id: str, character_id: str, persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a character to a channel."""
        return await self._request(
            "POST",
            "/api/v1/discord/characters/add",
            {
                "channel_id": channel_id,
                "character_id": character_id,
                "persona_id": persona_id or character_id,
            },
        )

    async def remove_character(self, channel_id: str, character_id: str) -> Dict[str, Any]:
        """Remove a character from a channel."""
        return await self._request(
            "POST",
            "/api/v1/discord/characters/remove",
            {"channel_id": channel_id, "character_id": character_id},
        )

    async def list_characters(self, channel_id: str) -> List[Dict[str, Any]]:
        """List all characters in a channel."""
        return await self._request(
            "GET", f"/api/v1/discord/characters/list?channel_id={channel_id}"
        )

    async def clear_history(
        self, channel_id: str, character_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear conversation history."""
        return await self._request(
            "POST",
            "/api/v1/discord/characters/clear-history",
            {"channel_id": channel_id, "character_id": character_id},
        )

    async def chat(
        self,
        channel_id: str,
        character_id: str,
        user_id: str,
        message: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a character response."""
        return await self._request(
            "POST",
            "/api/v1/discord/characters/chat",
            {
                "channel_id": channel_id,
                "character_id": character_id,
                "user_id": user_id,
                "message": message,
                "message_id": message_id,
            },
        )

    async def check_engagement(
        self, channel_id: str, character_id: str, recent_messages: List[str]
    ) -> Dict[str, Any]:
        """Check if a character should engage."""
        return await self._request(
            "POST",
            "/api/v1/discord/characters/engage",
            {
                "channel_id": channel_id,
                "character_id": character_id,
                "recent_messages": recent_messages,
            },
        )

    async def query_knowledge_store(self, query: str) -> Dict[str, Any]:
        """Query the RAG knowledge base using the conversational agent."""
        return await self._request("POST", "/api/v1/rag/agent", {"query": query})
