"""Token service for API token generation, validation, and management."""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Token prefix for easy identification
TOKEN_PREFIX = "lat_"  # Lambda API Token
TOKEN_LENGTH = 32  # 32 bytes = 64 hex chars


class TokenService:
    """Service for managing API tokens for automation authentication."""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize token service.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    @staticmethod
    def generate_token() -> str:
        """
        Generate a new API token.

        Returns:
            Token string with prefix (e.g., "lat_abc123...")
        """
        random_bytes = secrets.token_hex(TOKEN_LENGTH)
        return f"{TOKEN_PREFIX}{random_bytes}"

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for secure storage.

        Args:
            token: Plain text token

        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def is_valid_token_format(token: str) -> bool:
        """
        Check if a token has the correct format.

        Args:
            token: Token to validate

        Returns:
            True if token has valid format
        """
        if not token.startswith(TOKEN_PREFIX):
            return False
        token_part = token[len(TOKEN_PREFIX) :]
        return len(token_part) == TOKEN_LENGTH * 2  # hex encoding doubles length

    async def create_primary_token(self, user_id: UUID) -> str:
        """
        Create or regenerate the primary API token for a user.

        This replaces any existing primary token. The token is stored
        hashed in the profiles table.

        Args:
            user_id: User UUID

        Returns:
            The plain text token (only returned once, store it safely!)
        """
        token = self.generate_token()
        token_hash = self.hash_token(token)
        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE profiles
                SET api_token_hash = $1, api_token_created_at = $2, updated_at = $3
                WHERE id = $4
                """,
                token_hash,
                now,
                now,
                user_id,
            )

        logger.info(f"Created primary API token for user {user_id}")
        return token

    async def revoke_primary_token(self, user_id: UUID) -> bool:
        """
        Revoke the primary API token for a user.

        Args:
            user_id: User UUID

        Returns:
            True if a token was revoked, False if no token existed
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE profiles
                SET api_token_hash = NULL, api_token_created_at = NULL, updated_at = NOW()
                WHERE id = $1 AND api_token_hash IS NOT NULL
                """,
                user_id,
            )

        revoked = "UPDATE 1" in result
        if revoked:
            logger.info(f"Revoked primary API token for user {user_id}")
        return revoked

    async def get_primary_token_info(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Get metadata about the primary API token (not the token itself).

        Args:
            user_id: User UUID

        Returns:
            Token info dict or None if no token exists
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT api_token_hash IS NOT NULL as has_token, api_token_created_at
                FROM profiles WHERE id = $1
                """,
                user_id,
            )

        if not row or not row["has_token"]:
            return None

        return {
            "has_token": True,
            "created_at": (
                row["api_token_created_at"].isoformat() if row["api_token_created_at"] else None
            ),
            "token_prefix": TOKEN_PREFIX,
        }

    async def validate_primary_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a primary API token and return user info.

        Args:
            token: Plain text token to validate

        Returns:
            User info dict if valid, None otherwise
        """
        if not self.is_valid_token_format(token):
            return None

        token_hash = self.hash_token(token)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, role, tier, created_at,
                       mongodb_username, mongodb_password,
                       immich_user_id, immich_api_key, discord_user_id
                FROM profiles
                WHERE api_token_hash = $1
                """,
                token_hash,
            )

        if not row:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "role": row["role"] or "user",
            "tier": row["tier"] or "free",
            "created_at": row["created_at"],
            "mongodb_username": row["mongodb_username"],
            "mongodb_password": row["mongodb_password"],
            "immich_user_id": row["immich_user_id"],
            "immich_api_key": row["immich_api_key"],
            "discord_user_id": row["discord_user_id"],
        }

    # --- Named Tokens (api_tokens table) ---

    async def create_named_token(
        self,
        user_id: UUID,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        """
        Create a named API token for a user.

        Args:
            user_id: User UUID
            name: Token name (must be unique per user)
            scopes: Optional list of scopes/permissions
            expires_at: Optional expiration timestamp

        Returns:
            The plain text token (only returned once!)

        Raises:
            ValueError: If token name already exists
        """
        token = self.generate_token()
        token_hash = self.hash_token(token)

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO api_tokens (user_id, name, token_hash, scopes, expires_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    user_id,
                    name,
                    token_hash,
                    scopes or [],
                    expires_at,
                )
            except asyncpg.UniqueViolationError:
                raise ValueError(f"Token with name '{name}' already exists")

        logger.info(f"Created named API token '{name}' for user {user_id}")
        return token

    async def list_named_tokens(self, user_id: UUID) -> list[dict[str, Any]]:
        """
        List all named tokens for a user (without the actual token values).

        Args:
            user_id: User UUID

        Returns:
            List of token info dicts
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, scopes, expires_at, last_used_at, created_at
                FROM api_tokens
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id,
            )

        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "scopes": row["scopes"] or [],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    async def revoke_named_token(self, user_id: UUID, token_id: UUID) -> bool:
        """
        Revoke a named token by ID.

        Args:
            user_id: User UUID (for authorization)
            token_id: Token UUID to revoke

        Returns:
            True if token was revoked
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM api_tokens WHERE id = $1 AND user_id = $2",
                token_id,
                user_id,
            )

        revoked = "DELETE 1" in result
        if revoked:
            logger.info(f"Revoked named API token {token_id} for user {user_id}")
        return revoked

    async def revoke_named_token_by_name(self, user_id: UUID, name: str) -> bool:
        """
        Revoke a named token by name.

        Args:
            user_id: User UUID (for authorization)
            name: Token name to revoke

        Returns:
            True if token was revoked
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM api_tokens WHERE name = $1 AND user_id = $2",
                name,
                user_id,
            )

        revoked = "DELETE 1" in result
        if revoked:
            logger.info(f"Revoked named API token '{name}' for user {user_id}")
        return revoked

    async def validate_named_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a named API token and return user info.

        Also updates last_used_at timestamp.

        Args:
            token: Plain text token to validate

        Returns:
            User info dict with token scopes if valid, None otherwise
        """
        if not self.is_valid_token_format(token):
            return None

        token_hash = self.hash_token(token)

        async with self.pool.acquire() as conn:
            # Get token and user info in one query
            row = await conn.fetchrow(
                """
                SELECT t.id as token_id, t.name as token_name, t.scopes, t.expires_at,
                       p.id, p.email, p.role, p.tier, p.created_at,
                       p.mongodb_username, p.mongodb_password,
                       p.immich_user_id, p.immich_api_key, p.discord_user_id
                FROM api_tokens t
                JOIN profiles p ON t.user_id = p.id
                WHERE t.token_hash = $1
                """,
                token_hash,
            )

            if not row:
                return None

            # Check expiration
            if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
                return None

            # Update last_used_at
            await conn.execute(
                "UPDATE api_tokens SET last_used_at = NOW() WHERE id = $1",
                row["token_id"],
            )

        return {
            "id": row["id"],
            "email": row["email"],
            "role": row["role"] or "user",
            "tier": row["tier"] or "free",
            "created_at": row["created_at"],
            "mongodb_username": row["mongodb_username"],
            "mongodb_password": row["mongodb_password"],
            "immich_user_id": row["immich_user_id"],
            "immich_api_key": row["immich_api_key"],
            "discord_user_id": row["discord_user_id"],
            "token_name": row["token_name"],
            "token_scopes": row["scopes"] or [],
        }

    async def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate any API token (primary or named).

        Tries primary token first, then named tokens.

        Args:
            token: Plain text token to validate

        Returns:
            User info dict if valid, None otherwise
        """
        # Try primary token first (most common case)
        user_info = await self.validate_primary_token(token)
        if user_info:
            return user_info

        # Try named tokens
        return await self.validate_named_token(token)
