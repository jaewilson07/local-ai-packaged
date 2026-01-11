"""Immich API service for uploading ComfyUI-generated images."""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ImmichService:
    """Service for interacting with Immich API to upload and manage images."""

    def __init__(
        self,
        base_url: str,
        admin_api_key: str | None = None,
        http_client: aiohttp.ClientSession | None = None,
    ):
        """
        Initialize Immich service.

        Args:
            base_url: Immich server base URL (e.g., "http://immich-server:2283")
            admin_api_key: Admin API key for user provisioning (optional)
            http_client: Optional aiohttp client session (will create one if not provided)
        """
        self.base_url = base_url.rstrip("/")
        self.admin_api_key = admin_api_key
        self._http_client = http_client
        self._client_owned = http_client is None

    async def _get_http_client(self) -> aiohttp.ClientSession:
        """Get or create HTTP client session."""
        if self._http_client is None:
            self._http_client = aiohttp.ClientSession()
        return self._http_client

    async def close(self):
        """Close HTTP client session if we own it."""
        if self._client_owned and self._http_client:
            await self._http_client.close()
            self._http_client = None

    def _get_headers(self, api_key: str) -> dict[str, str]:
        """Get headers with API key."""
        return {"x-api-key": api_key}

    async def get_or_create_user(
        self, email: str, password: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get existing Immich user or create new one.

        Uses admin API key to create users if they don't exist.

        Args:
            email: User email address (1:1 mapping with Cloudflare Access)
            password: Optional password for new user (auto-generated if not provided)

        Returns:
            User dict with 'id' and 'apiKey' fields, or None if error
        """
        if not self.admin_api_key:
            logger.warning("No admin API key provided, cannot provision Immich users")
            return None

        client = await self._get_http_client()
        headers = self._get_headers(self.admin_api_key)

        try:
            # First, try to find user by email
            url = f"{self.base_url}/api/user"
            async with client.get(url, headers=headers) as response:
                if response.status == 200:
                    users = await response.json()
                    # Find user by email
                    for user in users:
                        if user.get("email") == email:
                            # User exists, get their API key
                            user_id = user.get("id")
                            if user_id:
                                api_key = await self._get_user_api_key(user_id, headers, client)
                                return {"id": user_id, "email": email, "apiKey": api_key}

            # User doesn't exist, create them
            logger.info(f"Creating Immich user for {email}")
            create_url = f"{self.base_url}/api/user"
            create_data = {
                "email": email,
                "password": password or self._generate_password(),
                "name": email.split("@")[0],  # Use email prefix as name
                "shouldChangePassword": False,
            }

            async with client.post(create_url, headers=headers, json=create_data) as response:
                if response.status in (200, 201):
                    user_data = await response.json()
                    user_id = user_data.get("id")
                    if user_id:
                        api_key = await self._get_user_api_key(user_id, headers, client)
                        return {"id": user_id, "email": email, "apiKey": api_key}
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create Immich user: {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting/creating Immich user: {e}")
            return None

    async def _get_user_api_key(
        self, user_id: str, headers: dict[str, str], client: aiohttp.ClientSession
    ) -> str | None:
        """Get or create API key for a user."""
        try:
            # Get existing API keys
            url = f"{self.base_url}/api/api-key"
            async with client.get(url, headers=headers) as response:
                if response.status == 200:
                    keys = await response.json()
                    # Find key for this user
                    for key in keys:
                        if key.get("userId") == user_id:
                            return key.get("key")

            # No key exists, create one
            create_url = f"{self.base_url}/api/api-key"
            create_data = {"name": "ComfyUI Integration", "userId": user_id}
            async with client.post(create_url, headers=headers, json=create_data) as response:
                if response.status in (200, 201):
                    key_data = await response.json()
                    return key_data.get("key")
                else:
                    logger.warning(f"Failed to create API key for user {user_id}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting user API key: {e}")
            return None

    def _generate_password(self) -> str:
        """Generate a random password for new Immich users."""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(32))

    async def upload_image(
        self, image_data: bytes, filename: str, api_key: str, description: str | None = None
    ) -> dict[str, Any] | None:
        """
        Upload an image to Immich.

        Args:
            image_data: Image file bytes
            filename: Filename for the image
            api_key: User's Immich API key
            description: Optional description for the image

        Returns:
            Asset metadata dict with 'id' field, or None if error
        """
        client = await self._get_http_client()
        headers = self._get_headers(api_key)
        url = f"{self.base_url}/api/asset/upload"

        try:
            data = aiohttp.FormData()
            data.add_field(
                "assetData",
                image_data,
                filename=filename,
                content_type="image/png",  # ComfyUI outputs PNG by default
            )
            if description:
                data.add_field("description", description)

            async with client.post(url, headers=headers, data=data) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    logger.info(
                        f"Uploaded image to Immich: {filename} (asset ID: {result.get('id')})"
                    )
                    return result
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to upload image to Immich: {response.status} - {error_text}"
                    )
                    return None

        except Exception as e:
            logger.exception(f"Error uploading image to Immich: {e}")
            return None

    async def upload_images_batch(
        self, images: list[dict[str, Any]], api_key: str, description_prefix: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Upload multiple images to Immich.

        Args:
            images: List of dicts with 'data' (bytes) and 'filename' (str) keys
            api_key: User's Immich API key
            description_prefix: Optional prefix for image descriptions

        Returns:
            List of uploaded asset metadata dicts
        """
        results = []
        for idx, image in enumerate(images):
            image_data = image.get("data")
            filename = image.get("filename", f"image_{idx}.png")
            description = None
            if description_prefix:
                description = f"{description_prefix} - {filename}"

            result = await self.upload_image(
                image_data=image_data, filename=filename, api_key=api_key, description=description
            )
            if result:
                results.append(result)

        return results

    async def get_user_stats(self, api_key: str) -> dict[str, Any] | None:
        """
        Get user statistics from Immich.

        Args:
            api_key: User's Immich API key

        Returns:
            Stats dict with photo/video counts, or None if error
        """
        client = await self._get_http_client()
        headers = self._get_headers(api_key)
        url = f"{self.base_url}/api/user/me"

        try:
            async with client.get(url, headers=headers) as response:
                if response.status == 200:
                    await response.json()
                    # Get asset counts
                    assets_url = f"{self.base_url}/api/asset"
                    async with client.get(
                        assets_url, headers=headers, params={"take": 1}
                    ) as assets_response:
                        if assets_response.status == 200:
                            assets_data = await assets_response.json()
                            total_assets = assets_data.get("total", 0)

                            return {
                                "total_photos": total_assets,  # Simplified - Immich doesn't separate in this endpoint
                                "total_videos": 0,  # Would need separate query
                                "total_albums": 0,  # Would need separate query
                                "total_size_bytes": 0,  # Would need to sum asset sizes
                            }
                    return {
                        "total_photos": 0,
                        "total_videos": 0,
                        "total_albums": 0,
                        "total_size_bytes": 0,
                    }
                else:
                    logger.error(f"Failed to get Immich user stats: {response.status}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting Immich user stats: {e}")
            return None
