"""Supabase user provisioning service."""

import logging
from datetime import datetime
from uuid import uuid4

import asyncpg

from server.projects.auth.config import AuthConfig
from server.projects.auth.models import User

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for Supabase user provisioning and management."""

    def __init__(self, config: AuthConfig):
        """
        Initialize Supabase service.

        Args:
            config: Auth configuration with Supabase settings
        """
        self.config = config
        self.db_url = config.supabase_db_url
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            if not self.db_url:
                raise ValueError("Supabase DB URL not configured")

            self._pool = await asyncpg.create_pool(
                self.db_url, min_size=1, max_size=5, command_timeout=10
            )
            logger.info("Created Supabase connection pool")

        return self._pool

    async def _ensure_profiles_table(self) -> None:
        """Ensure profiles table exists with required schema."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'profiles'
                )
            """
            )

            if not table_exists:
                logger.info("Creating profiles table")
                await conn.execute(
                    """
                    CREATE TABLE profiles (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email TEXT UNIQUE NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        tier TEXT NOT NULL DEFAULT 'free',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """
                )

                # Create index on email for fast lookups
                await conn.execute(
                    """
                    CREATE INDEX idx_profiles_email ON profiles(email)
                """
                )

                logger.info("Created profiles table with indexes")
            else:
                # Check if mongodb_username and mongodb_password columns exist, add if not
                mongodb_username_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'profiles'
                        AND column_name = 'mongodb_username'
                    )
                """
                )

                if not mongodb_username_exists:
                    logger.info("Adding MongoDB credential columns to profiles table")
                    await conn.execute(
                        """
                        ALTER TABLE profiles
                        ADD COLUMN mongodb_username TEXT,
                        ADD COLUMN mongodb_password TEXT
                    """
                    )
                    logger.info("Added MongoDB credential columns")

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User object if found, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, role, tier, created_at, mongodb_username, mongodb_password
                FROM profiles
                WHERE email = $1
            """,
                email,
            )

            if row:
                user = User(
                    id=row["id"],
                    email=row["email"],
                    role=row["role"],
                    tier=row["tier"],
                    created_at=str(row["created_at"]) if row["created_at"] else None,
                )
                # Store MongoDB credentials in user object if available
                if hasattr(user, "__dict__"):
                    user.__dict__["mongodb_username"] = row.get("mongodb_username")
                    user.__dict__["mongodb_password"] = row.get("mongodb_password")
                return user

        return None

    async def create_user(
        self,
        email: str,
        role: str = "user",
        tier: str = "free",
        mongodb_username: str | None = None,
        mongodb_password: str | None = None,
    ) -> User:
        """
        Create a new user in Supabase.

        Args:
            email: User email address
            role: User role (default: "user")
            tier: User tier (default: "free")
            mongodb_username: MongoDB username (optional)
            mongodb_password: MongoDB password (optional)

        Returns:
            Created User object
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            user_id = uuid4()
            now = datetime.now()

            await conn.execute(
                """
                INSERT INTO profiles (id, email, role, tier, created_at, updated_at, mongodb_username, mongodb_password)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                user_id,
                email,
                role,
                tier,
                now,
                now,
                mongodb_username,
                mongodb_password,
            )

            logger.info(f"Created user {email} with ID {user_id}")

            user = User(id=user_id, email=email, role=role, tier=tier, created_at=now.isoformat())
            # Store MongoDB credentials in user object
            if hasattr(user, "__dict__"):
                user.__dict__["mongodb_username"] = mongodb_username
                user.__dict__["mongodb_password"] = mongodb_password
            return user

    async def update_mongodb_credentials(
        self, email: str, mongodb_username: str, mongodb_password: str
    ) -> None:
        """
        Update MongoDB credentials for a user.

        Args:
            email: User email address
            mongodb_username: MongoDB username
            mongodb_password: MongoDB password
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE profiles
                SET mongodb_username = $1, mongodb_password = $2, updated_at = NOW()
                WHERE email = $3
            """,
                mongodb_username,
                mongodb_password,
                email,
            )

            logger.info(f"Updated MongoDB credentials for {email}")

    async def get_or_provision_user(self, email: str) -> User:
        """
        Get existing user or provision new one (JIT provisioning).

        Args:
            email: User email address

        Returns:
            User object (existing or newly created)
        """
        # Ensure table exists
        await self._ensure_profiles_table()

        # Try to get existing user
        user = await self.get_user_by_email(email)

        if user:
            return user

        # User doesn't exist, provision new one
        logger.info(f"Provisioning new user: {email}")
        return await self.create_user(email)

    async def is_admin(self, email: str) -> bool:
        """
        Check if user is an admin.

        Args:
            email: User email address

        Returns:
            True if user has admin role, False otherwise
        """
        user = await self.get_user_by_email(email)
        return user is not None and user.role == "admin"

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed Supabase connection pool")
