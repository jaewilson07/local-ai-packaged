"""Immich user provisioning service for auth project."""

import logging

import aiohttp
from services.auth.config import AuthConfig

from shared.security import generate_secure_password

logger = logging.getLogger(__name__)


class ImmichService:
    """Service for Immich user provisioning during JIT authentication."""

    def __init__(self, config: AuthConfig):
        """
        Initialize Immich service.

        Args:
            config: Auth configuration with Immich settings
        """
        self.config = config
        self.base_url = config.immich_base_url.rstrip("/")
        self.admin_api_key = config.immich_admin_api_key
        self._http_client: aiohttp.ClientSession | None = None

    async def _get_http_client(self) -> aiohttp.ClientSession:
        """Get or create HTTP client session."""
        if self._http_client is None:
            self._http_client = aiohttp.ClientSession()
        return self._http_client

    async def close(self):
        """Close HTTP client session."""
        if self._http_client:
            await self._http_client.close()
            self._http_client = None

    def _get_headers(self, api_key: str) -> dict[str, str]:
        """Get headers with API key."""
        return {"x-api-key": api_key}

    async def provision_user(self, email: str, user_id: str) -> tuple[str, str]:
        """
        Provision Immich user and generate API key (JIT provisioning).

        Creates user if they don't exist, then gets or creates API key.

        Args:
            email: User email address (1:1 mapping with Cloudflare Access)
            user_id: User UUID (for reference, not used by Immich)

        Returns:
            Tuple of (immich_user_id, immich_api_key)

        Raises:
            RuntimeError: If provisioning fails
        """
        if not self.admin_api_key:
            raise RuntimeError("No admin API key provided, cannot provision Immich users")

        client = await self._get_http_client()
        headers = self._get_headers(self.admin_api_key)

        try:
            # First, try to find user by email using the admin endpoint (Immich v2.x)
            # Try both old and new API endpoints for compatibility
            search_url = f"{self.base_url}/api/admin/users"
            async with client.get(search_url, headers=headers) as response:
                if response.status == 200:
                    users = await response.json()
                    # Find user by email
                    for user in users:
                        if user.get("email") == email:
                            # User exists, get their API key
                            immich_user_id = user.get("id")
                            if immich_user_id:
                                api_key = await self._get_user_api_key(
                                    immich_user_id, headers, client
                                )
                                if api_key:
                                    return (immich_user_id, api_key)
                                raise RuntimeError(
                                    f"Failed to get API key for existing Immich user {email}"
                                )
                elif response.status == 404:
                    # Try old endpoint for older Immich versions
                    old_url = f"{self.base_url}/api/user"
                    async with client.get(old_url, headers=headers) as old_response:
                        if old_response.status == 200:
                            users = await old_response.json()
                            for user in users:
                                if user.get("email") == email:
                                    immich_user_id = user.get("id")
                                    if immich_user_id:
                                        api_key = await self._get_user_api_key(
                                            immich_user_id, headers, client
                                        )
                                        if api_key:
                                            return (immich_user_id, api_key)

            # User doesn't exist, create them using admin endpoint (Immich v2.x)
            logger.info(f"Creating Immich user for {email}")
            create_url = f"{self.base_url}/api/admin/users"
            create_data = {
                "email": email,
                "password": generate_secure_password(),
                "name": email.split("@")[0],  # Use email prefix as name
                "shouldChangePassword": False,
            }

            async with client.post(create_url, headers=headers, json=create_data) as response:
                if response.status in (200, 201):
                    user_data = await response.json()
                    immich_user_id = user_data.get("id")
                    if immich_user_id:
                        api_key = await self._get_user_api_key(immich_user_id, headers, client)
                        if api_key:
                            return (immich_user_id, api_key)
                        raise RuntimeError(f"Failed to create API key for new Immich user {email}")
                    raise RuntimeError(f"Immich user created but no user ID returned for {email}")

                # Try old endpoint for older Immich versions
                if response.status == 404:
                    old_create_url = f"{self.base_url}/api/user"
                    async with client.post(
                        old_create_url, headers=headers, json=create_data
                    ) as old_response:
                        if old_response.status in (200, 201):
                            user_data = await old_response.json()
                            immich_user_id = user_data.get("id")
                            if immich_user_id:
                                api_key = await self._get_user_api_key(
                                    immich_user_id, headers, client
                                )
                                if api_key:
                                    return (immich_user_id, api_key)
                        error_text = await old_response.text()
                        raise RuntimeError(
                            f"Failed to create Immich user (old API): {old_response.status} - {error_text}"
                        )

                error_text = await response.text()
                raise RuntimeError(
                    f"Failed to create Immich user: {response.status} - {error_text}"
                )

        except RuntimeError:
            raise
        except Exception as e:
            logger.exception("Error provisioning Immich user")
            raise RuntimeError(f"Immich provisioning failed: {e}") from e

    async def _get_user_api_key(
        self, user_id: str, headers: dict[str, str], client: aiohttp.ClientSession
    ) -> str | None:
        """Get or create API key for a user.

        Note: Immich only returns the API key secret once at creation time.
        We can't retrieve existing keys, so we always create a new one.
        """
        try:
            # Create a new API key for this user
            # Use /api/api-keys endpoint (Immich v2.x)
            create_url = f"{self.base_url}/api/api-keys"
            create_data = {
                "name": f"Cloudflare Access Integration ({user_id[:8]})",
                "permissions": ["all"],
            }
            async with client.post(create_url, headers=headers, json=create_data) as response:
                if response.status in (200, 201):
                    key_data = await response.json()
                    # The secret is returned in the 'secret' field
                    secret = key_data.get("secret")
                    if secret:
                        logger.info(f"Created API key for Immich user {user_id}")
                        return secret
                    logger.warning(f"API key created but no secret returned for user {user_id}")
                    return None

                # Try old endpoint for older Immich versions
                if response.status == 404:
                    old_url = f"{self.base_url}/api/api-key"
                    async with client.post(
                        old_url, headers=headers, json=create_data
                    ) as old_response:
                        if old_response.status in (200, 201):
                            key_data = await old_response.json()
                            return key_data.get("secret") or key_data.get("key")
                        error_text = await old_response.text()
                        logger.warning(
                            f"Failed to create API key (old API): {old_response.status} - {error_text}"
                        )
                        return None

                error_text = await response.text()
                logger.warning(
                    f"Failed to create API key for user {user_id}: {response.status} - {error_text}"
                )
                return None

        except Exception:
            logger.exception("Error creating user API key")
            return None

    async def upload_asset(
        self,
        user_api_key: str,
        file_data: bytes,
        filename: str,
        device_asset_id: str | None = None,
        device_id: str = "comfyui-lambda",
    ) -> str | None:
        """
        Upload an asset (image/video) to Immich using the user's API key.

        Args:
            user_api_key: User's Immich API key
            file_data: File content as bytes
            filename: Original filename
            device_asset_id: Unique ID for this asset (defaults to filename)
            device_id: Device identifier (defaults to "comfyui-lambda")

        Returns:
            Immich asset ID if successful, None otherwise
        """
        if not user_api_key:
            logger.warning("No Immich API key provided for upload")
            return None

        client = await self._get_http_client()
        headers = self._get_headers(user_api_key)

        # Use filename as device_asset_id if not provided
        if device_asset_id is None:
            device_asset_id = filename

        try:
            from datetime import datetime, timezone

            import aiohttp

            # Immich upload endpoint requires multipart form data
            # Use /api/assets for Immich v2.x (previously /api/asset/upload)
            upload_url = f"{self.base_url}/api/assets"

            # Determine content type from filename
            content_type = "image/png"
            lower_filename = filename.lower()
            if lower_filename.endswith(".jpg") or lower_filename.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif lower_filename.endswith(".webp"):
                content_type = "image/webp"
            elif lower_filename.endswith(".gif"):
                content_type = "image/gif"

            # Build multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field(
                "assetData",
                file_data,
                filename=filename,
                content_type=content_type,
            )
            form_data.add_field("deviceAssetId", device_asset_id)
            form_data.add_field("deviceId", device_id)
            form_data.add_field("fileCreatedAt", datetime.now(timezone.utc).isoformat())
            form_data.add_field("fileModifiedAt", datetime.now(timezone.utc).isoformat())

            # Don't include Content-Type in headers for multipart
            upload_headers = {"x-api-key": user_api_key}

            async with client.post(upload_url, headers=upload_headers, data=form_data) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    asset_id = result.get("id")
                    if asset_id:
                        logger.info(f"Uploaded asset to Immich: {asset_id} ({filename})")
                        return asset_id
                    logger.warning("Immich upload succeeded but no asset ID returned")
                    return None
                error_text = await response.text()
                logger.warning(
                    f"Failed to upload to Immich: {response.status} - {error_text[:200]}"
                )
                return None

        except Exception as e:
            logger.exception(f"Error uploading asset to Immich: {e}")
            return None

    async def get_user_statistics(self, user_api_key: str) -> dict | None:
        """
        Get user statistics from Immich API.

        Uses the user's API key to fetch their personal statistics including
        photo/video counts and storage usage.

        Args:
            user_api_key: User's Immich API key

        Returns:
            Dictionary with statistics or None if request fails
        """
        if not user_api_key:
            return None

        client = await self._get_http_client()
        headers = self._get_headers(user_api_key)

        try:
            # Get user info (includes quota info)
            user_url = f"{self.base_url}/api/users/me"
            async with client.get(user_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get Immich user info: {response.status}")
                    return None
                user_data = await response.json()

            # Get asset statistics
            stats_url = f"{self.base_url}/api/assets/statistics"
            async with client.get(stats_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get Immich statistics: {response.status}")
                    # Return partial data if we have user info
                    return {
                        "total_photos": 0,
                        "total_videos": 0,
                        "total_size_bytes": user_data.get("quotaUsageInBytes", 0),
                        "name": user_data.get("name", ""),
                        "email": user_data.get("email", ""),
                    }
                stats_data = await response.json()

            # Get album count
            albums_url = f"{self.base_url}/api/albums"
            async with client.get(albums_url, headers=headers) as response:
                if response.status == 200:
                    albums = await response.json()
                    album_count = len(albums) if isinstance(albums, list) else 0
                else:
                    album_count = 0

            return {
                "total_photos": stats_data.get("images", 0),
                "total_videos": stats_data.get("videos", 0),
                "total_size_bytes": user_data.get("quotaUsageInBytes", 0),
                "total_albums": album_count,
                "name": user_data.get("name", ""),
                "email": user_data.get("email", ""),
            }

        except aiohttp.ClientError as e:
            logger.warning(f"Failed to connect to Immich server: {e}")
            return None
        except Exception:
            logger.exception("Error getting Immich user statistics")
            return None
