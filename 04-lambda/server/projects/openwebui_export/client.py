"""Open WebUI API client."""

import logging
from typing import Any

import httpx

from server.projects.openwebui_export.config import config

logger = logging.getLogger(__name__)


class OpenWebUIClient:
    """Client for interacting with Open WebUI API."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        """
        Initialize Open WebUI client.

        Args:
            api_url: Open WebUI API URL (defaults to config)
            api_key: API key for authentication (optional)
        """
        self.api_url = api_url or config.openwebui_api_url
        self.api_key = api_key or config.openwebui_api_key
        self.base_url = f"{self.api_url.rstrip('/')}/api/v1"

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication if available."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def get_conversations(
        self, user_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get list of conversations from Open WebUI.

        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of conversations to return
            offset: Offset for pagination

        Returns:
            List of conversation dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"limit": limit, "offset": offset}
                if user_id:
                    params["user_id"] = user_id

                response = await client.get(
                    f"{self.base_url}/conversations", headers=self._get_headers(), params=params
                )
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        except Exception as e:
            logger.exception(f"Failed to get conversations: {e}")
            raise

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """
        Get a specific conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}", headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.exception(f"Failed to get conversation {conversation_id}: {e}")
            raise

    async def update_conversation_topics(self, conversation_id: str, topics: list[str]) -> bool:
        """
        Update conversation topics in Open WebUI.

        Args:
            conversation_id: Conversation ID
            topics: List of topic strings

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Note: This endpoint may need to be verified with Open WebUI API docs
                response = await client.patch(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self._get_headers(),
                    json={"topics": topics},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.exception(f"Failed to update conversation topics: {e}")
            return False
