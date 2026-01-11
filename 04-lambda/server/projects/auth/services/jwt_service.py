"""JWT validation service for Cloudflare Access."""

import json
import logging
from datetime import datetime, timedelta

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from server.projects.auth.config import AuthConfig

logger = logging.getLogger(__name__)


class JWTService:
    """Service for validating Cloudflare Access JWTs."""

    def __init__(self, config: AuthConfig):
        """
        Initialize JWT service.

        Args:
            config: Auth configuration with Cloudflare settings
        """
        self.config = config
        self.certs_url = f"{config.cloudflare_auth_domain}/cdn-cgi/access/certs"
        self.audience = config.cloudflare_aud_tag
        self.team_domain = config.cloudflare_auth_domain

        # Cache for public keys (refresh every hour)
        self._public_keys: list | None = None
        self._keys_cache_time: datetime | None = None
        self._keys_cache_ttl = timedelta(hours=1)

    async def _get_public_keys(self) -> list:
        """
        Fetch and cache public keys from Cloudflare.

        Returns:
            List of RSA public keys usable by PyJWT
        """
        # Return cached keys if still valid
        if self._public_keys and self._keys_cache_time:
            if datetime.now() - self._keys_cache_time < self._keys_cache_ttl:
                return self._public_keys

        # Fetch fresh keys
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.certs_url)
                response.raise_for_status()
                jwk_set = response.json()

            public_keys = []
            for key_dict in jwk_set.get("keys", []):
                try:
                    public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))
                    public_keys.append(public_key)
                except Exception as e:
                    logger.warning(f"Failed to parse public key: {e}")
                    continue

            # Update cache
            self._public_keys = public_keys
            self._keys_cache_time = datetime.now()

            logger.info(f"Fetched {len(public_keys)} public keys from Cloudflare")
            return public_keys

        except Exception as e:
            logger.exception(f"Failed to fetch public keys: {e}")
            # Return cached keys if available, even if expired
            if self._public_keys:
                logger.warning("Using cached public keys due to fetch failure")
                return self._public_keys
            raise

    async def validate_and_extract_email(self, token: str) -> str:
        """
        Validate JWT token and extract email from payload.

        Args:
            token: JWT token string from Cf-Access-Jwt-Assertion header

        Returns:
            Email address from token payload

        Raises:
            ValueError: If token is invalid or missing required claims
        """
        if not self.audience:
            raise ValueError("Missing required audience (CLOUDFLARE_AUD_TAG)")

        if not self.team_domain:
            raise ValueError("Missing required team domain (CLOUDFLARE_AUTH_DOMAIN)")

        # Get public keys
        keys = await self._get_public_keys()

        if not keys:
            raise ValueError("No public keys available for validation")

        # Try to decode with each key
        last_error = None
        for key in keys:
            try:
                # Decode and validate token
                payload = jwt.decode(
                    token,
                    key=key,
                    audience=self.audience,
                    algorithms=["RS256"],
                    issuer=self.team_domain,
                )

                # Extract email from payload
                email = payload.get("email")
                if not email:
                    raise ValueError("Token payload missing 'email' claim")

                logger.debug(f"Successfully validated JWT for {email}")
                return email

            except jwt.ExpiredSignatureError:
                raise ValueError("Token has expired")
            except jwt.InvalidAudienceError:
                raise ValueError(f"Token audience does not match expected: {self.audience}")
            except jwt.InvalidIssuerError:
                raise ValueError(f"Token issuer does not match expected: {self.team_domain}")
            except jwt.InvalidSignatureError:
                # Try next key
                last_error = "Invalid signature"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        # If we get here, all keys failed
        raise ValueError(f"Token validation failed: {last_error}")
