"""Immich user provisioning service for auth project."""

import logging

import aiohttp
from services.auth.config import AuthConfig

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

    def _generate_password(self) -> str:
        """Generate a random password for new Immich users."""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(32))

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
            # First, try to find user by email
            url = f"{self.base_url}/api/user"
            async with client.get(url, headers=headers) as response:
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

            # User doesn't exist, create them
            logger.info(f"Creating Immich user for {email}")
            create_url = f"{self.base_url}/api/user"
            create_data = {
                "email": email,
                "password": self._generate_password(),
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
            create_data = {"name": "Cloudflare Access Integration", "userId": user_id}
            async with client.post(create_url, headers=headers, json=create_data) as response:
                if response.status in (200, 201):
                    key_data = await response.json()
                    return key_data.get("key")
                logger.warning(f"Failed to create API key for user {user_id}")
                return None

        except Exception:
            logger.exception("Error getting user API key")
            return None
