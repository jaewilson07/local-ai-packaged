"""JWT validation service for Cloudflare Access."""

import json
import logging
from datetime import datetime, timedelta

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from services.auth.config import AuthConfig

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

    async def _get_public_keys(self, force_refresh: bool = False) -> list:
        """
        Fetch and cache public keys from Cloudflare.

        Args:
            force_refresh: If True, bypass cache and fetch fresh keys

        Returns:
            List of RSA public keys usable by PyJWT
        """
        # Return cached keys if still valid (unless force refresh requested)
        if not force_refresh and self._public_keys and self._keys_cache_time:
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

        except Exception:
            logger.exception("Failed to fetch public keys")
            # Return cached keys if available, even if expired
            if self._public_keys:
                logger.warning("Using cached public keys due to fetch failure")
                return self._public_keys
            raise

    async def _try_validate_with_keys(
        self, token: str, keys: list
    ) -> tuple[str | None, str | None]:
        """
        Try to validate token with a list of keys.

        Args:
            token: JWT token string
            keys: List of public keys to try

        Returns:
            Tuple of (email, error). If validation succeeds, returns (email, None).
            If validation fails, returns (None, error_message).
        """
        last_error = None
        for key in keys:
            try:
                payload = jwt.decode(
                    token,
                    key=key,
                    audience=self.audience,
                    algorithms=["RS256"],
                    issuer=self.team_domain,
                )

                email = payload.get("email")
                if not email:
                    return None, "Token payload missing 'email' claim"

                logger.debug(f"Successfully validated JWT for {email}")
                return email, None

            except jwt.ExpiredSignatureError:
                return None, "Token has expired"
            except jwt.InvalidAudienceError:
                return None, f"Token audience does not match expected: {self.audience}"
            except jwt.InvalidIssuerError:
                return None, f"Token issuer does not match expected: {self.team_domain}"
            except jwt.InvalidSignatureError:
                last_error = "Invalid signature"
                logger.debug(f"Key {keys.index(key) + 1}/{len(keys)} failed signature validation")
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return None, last_error

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

        # Get public keys (from cache if available)
        keys = await self._get_public_keys()

        if not keys:
            raise ValueError("No public keys available for validation")

        # Try to validate with cached keys
        email, error = await self._try_validate_with_keys(token, keys)

        if email:
            return email

        # If signature validation failed, try refreshing keys (handles key rotation)
        if error == "Invalid signature":
            logger.info("Signature validation failed with cached keys, fetching fresh keys...")
            fresh_keys = await self._get_public_keys(force_refresh=True)

            # Only retry if we got different keys
            if fresh_keys and fresh_keys != keys:
                logger.info(f"Retrying validation with {len(fresh_keys)} fresh keys")
                email, error = await self._try_validate_with_keys(token, fresh_keys)
                if email:
                    return email

        # If we get here, validation failed even after refresh
        # Log additional diagnostic info
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            token_aud = unverified.get("aud", [])
            token_iss = unverified.get("iss", "unknown")
            token_exp = unverified.get("exp", 0)
            exp_time = datetime.fromtimestamp(token_exp) if token_exp else None
            logger.warning(
                f"JWT validation failed after trying all keys (including fresh fetch). "
                f"Token iss={token_iss}, aud={token_aud}, exp={exp_time}. "
                f"Expected aud={self.audience}, iss={self.team_domain}. "
                f"This may indicate a stale browser token - user should clear cookies."
            )
        except Exception as decode_err:
            logger.warning(f"Could not decode token for diagnostics: {decode_err}")

        raise ValueError(f"Token validation failed: {error}")
