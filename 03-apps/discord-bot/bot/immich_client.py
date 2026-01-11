"""Immich API client."""

from datetime import datetime

import aiohttp

from bot.config import config


class ImmichClient:
    """Client for Immich API operations."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or config.IMMICH_SERVER_URL).rstrip("/")
        self.api_key = api_key or config.IMMICH_API_KEY
        self.headers = {"x-api-key": self.api_key}

    async def upload_asset(
        self, file_data: bytes, filename: str, description: str | None = None
    ) -> dict:
        """Upload asset to Immich."""
        url = f"{self.base_url}/api/asset/upload"
        data = aiohttp.FormData()
        data.add_field(
            "assetData", file_data, filename=filename, content_type="application/octet-stream"
        )
        if description:
            data.add_field("description", description)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, data=data) as response:
                response.raise_for_status()
                return await response.json()

    async def search_people(self, name: str) -> list[dict]:
        """Search for people by name in Immich."""
        url = f"{self.base_url}/api/person"
        params = {"withHidden": "false"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                people = await response.json()
                # Filter by name (case-insensitive partial match)
                name_lower = name.lower()
                filtered = [
                    person for person in people if name_lower in person.get("name", "").lower()
                ]
                return filtered[:10]  # Limit to 10 results

    async def get_person_thumbnail(self, person_id: str) -> str | None:
        """Get thumbnail URL for a person."""
        url = f"{self.base_url}/api/person/{person_id}/thumbnail"
        return f"{url}?x-api-key={self.api_key}"

    async def get_asset_faces(self, asset_id: str) -> list[dict]:
        """Get face detections for an asset."""
        url = f"{self.base_url}/api/asset/{asset_id}/faces"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 404:
                    return []  # No faces detected
                response.raise_for_status()
                return await response.json()

    async def list_new_assets(self, since: datetime) -> list[dict]:
        """List assets created or updated after a timestamp."""
        url = f"{self.base_url}/api/asset"
        # Convert datetime to ISO format timestamp
        timestamp = since.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        params = {"updatedAfter": timestamp}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                response.raise_for_status()
                result = await response.json()
                # Response is paginated, return items
                return result.get("items", [])

    async def get_asset_thumbnail(self, asset_id: str) -> str | None:
        """Get thumbnail URL for an asset."""
        url = f"{self.base_url}/api/asset/{asset_id}/thumbnail"
        return f"{url}?x-api-key={self.api_key}"

    async def get_asset_info(self, asset_id: str) -> dict:
        """Get asset information."""
        url = f"{self.base_url}/api/asset/{asset_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()
