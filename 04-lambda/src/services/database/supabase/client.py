"""Supabase database client."""

import logging
from datetime import datetime
from uuid import uuid4

import asyncpg
from services.auth.models import User

from .config import SupabaseConfig

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for Supabase PostgreSQL database operations."""

    def __init__(self, config: SupabaseConfig):
        """
        Initialize Supabase client.

        Args:
            config: Supabase configuration
        """
        self.config = config
        self.db_url = config.db_url
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

    async def ensure_profiles_table(self) -> None:
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
                # Ensure credential columns exist (migrations)
                await self._ensure_credential_columns(conn)

    async def _ensure_credential_columns(self, conn: asyncpg.Connection) -> None:
        """Ensure credential columns exist in profiles table."""
        # MongoDB credentials
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

        # Immich credentials
        immich_user_id_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'profiles'
                AND column_name = 'immich_user_id'
            )
        """
        )

        if not immich_user_id_exists:
            logger.info("Adding Immich credential columns to profiles table")
            await conn.execute(
                """
                ALTER TABLE profiles
                ADD COLUMN immich_user_id TEXT,
                ADD COLUMN immich_api_key TEXT
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_profiles_immich_user_id
                ON profiles(immich_user_id)
                WHERE immich_user_id IS NOT NULL
            """
            )
            logger.info("Added Immich credential columns")

        # Discord user ID
        discord_user_id_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'profiles'
                AND column_name = 'discord_user_id'
            )
        """
        )

        if not discord_user_id_exists:
            logger.info("Adding Discord user ID column to profiles table")
            await conn.execute(
                """
                ALTER TABLE profiles
                ADD COLUMN discord_user_id TEXT
            """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_profiles_discord_user_id
                ON profiles(discord_user_id)
                WHERE discord_user_id IS NOT NULL
            """
            )
            logger.info("Added Discord user ID column")

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
                SELECT id, email, role, tier, created_at, mongodb_username, mongodb_password,
                       immich_user_id, immich_api_key, discord_user_id
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
                # Store credentials in user object
                if hasattr(user, "__dict__"):
                    user.__dict__["mongodb_username"] = row.get("mongodb_username")
                    user.__dict__["mongodb_password"] = row.get("mongodb_password")
                    user.__dict__["immich_user_id"] = row.get("immich_user_id")
                    user.__dict__["immich_api_key"] = row.get("immich_api_key")
                    user.__dict__["discord_user_id"] = row.get("discord_user_id")
                return user

        return None

    async def get_user_by_discord_id(self, discord_user_id: str) -> User | None:
        """
        Get user by Discord user ID.

        Args:
            discord_user_id: Discord user ID

        Returns:
            User object if found, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, role, tier, created_at, mongodb_username, mongodb_password,
                       immich_user_id, immich_api_key, discord_user_id
                FROM profiles
                WHERE discord_user_id = $1
            """,
                discord_user_id,
            )

            if row:
                user = User(
                    id=row["id"],
                    email=row["email"],
                    role=row["role"],
                    tier=row["tier"],
                    created_at=str(row["created_at"]) if row["created_at"] else None,
                )
                # Store credentials in user object
                if hasattr(user, "__dict__"):
                    user.__dict__["mongodb_username"] = row.get("mongodb_username")
                    user.__dict__["mongodb_password"] = row.get("mongodb_password")
                    user.__dict__["immich_user_id"] = row.get("immich_user_id")
                    user.__dict__["immich_api_key"] = row.get("immich_api_key")
                    user.__dict__["discord_user_id"] = row.get("discord_user_id")
                return user

        return None

    async def create_user(
        self,
        email: str,
        role: str = "user",
        tier: str = "free",
        mongodb_username: str | None = None,
        mongodb_password: str | None = None,
        immich_user_id: str | None = None,
        immich_api_key: str | None = None,
    ) -> User:
        """
        Create a new user in Supabase.

        Args:
            email: User email address
            role: User role (default: "user")
            tier: User tier (default: "free")
            mongodb_username: MongoDB username (optional)
            mongodb_password: MongoDB password (optional)
            immich_user_id: Immich user ID (optional)
            immich_api_key: Immich API key (optional)

        Returns:
            Created User object
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            user_id = uuid4()
            now = datetime.now()

            await conn.execute(
                """
                INSERT INTO profiles (id, email, role, tier, created_at, updated_at,
                                    mongodb_username, mongodb_password,
                                    immich_user_id, immich_api_key)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                user_id,
                email,
                role,
                tier,
                now,
                now,
                mongodb_username,
                mongodb_password,
                immich_user_id,
                immich_api_key,
            )

            logger.info(f"Created user {email} with ID {user_id}")

            user = User(id=user_id, email=email, role=role, tier=tier, created_at=now.isoformat())
            # Store credentials in user object
            if hasattr(user, "__dict__"):
                user.__dict__["mongodb_username"] = mongodb_username
                user.__dict__["mongodb_password"] = mongodb_password
                user.__dict__["immich_user_id"] = immich_user_id
                user.__dict__["immich_api_key"] = immich_api_key
            return user

    async def update_mongodb_credentials(
        self, email: str, mongodb_username: str, mongodb_password: str
    ) -> None:
        """Update MongoDB credentials for a user."""
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

    async def get_immich_credentials(self, email: str) -> tuple[str | None, str | None]:
        """Get Immich credentials for a user."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT immich_user_id, immich_api_key
                FROM profiles
                WHERE email = $1
            """,
                email,
            )

            if row:
                return (row.get("immich_user_id"), row.get("immich_api_key"))

        return (None, None)

    async def update_immich_credentials(
        self, email: str, immich_user_id: str, immich_api_key: str
    ) -> None:
        """Update Immich credentials for a user."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE profiles
                SET immich_user_id = $1, immich_api_key = $2, updated_at = NOW()
                WHERE email = $3
            """,
                immich_user_id,
                immich_api_key,
                email,
            )

            logger.info(f"Updated Immich credentials for {email}")

    async def update_discord_user_id(self, email: str, discord_user_id: str) -> None:
        """Update Discord user ID for a user."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE profiles
                SET discord_user_id = $1, updated_at = NOW()
                WHERE email = $2
            """,
                discord_user_id,
                email,
            )

            logger.info(f"Updated Discord user ID for {email}")

    async def get_or_provision_user(self, email: str) -> User:
        """
        Get existing user or provision new one (JIT provisioning).

        Args:
            email: User email address

        Returns:
            User object (existing or newly created)
        """
        # Ensure table exists
        await self.ensure_profiles_table()

        # Try to get existing user
        user = await self.get_user_by_email(email)

        if user:
            return user

        # User doesn't exist, provision new one
        logger.info(f"Provisioning new user: {email}")
        return await self.create_user(email)

    async def is_admin(self, email: str) -> bool:
        """Check if user is an admin."""
        user = await self.get_user_by_email(email)
        return user is not None and user.role == "admin"

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed Supabase connection pool")
