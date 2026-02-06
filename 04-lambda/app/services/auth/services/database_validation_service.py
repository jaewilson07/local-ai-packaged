"""Database validation and migration service for Supabase."""

import logging
from pathlib import Path

import asyncpg
from app.services.auth.config import AuthConfig

logger = logging.getLogger(__name__)


class DatabaseValidationService:
    """Service for validating database schema and applying migrations."""

    # Core tables required for system to function
    CORE_TABLES = [
        "profiles",  # Required for authentication
    ]

    # Optional tables (warn if missing but don't fail)
    OPTIONAL_TABLES = [
        "comfyui_workflows",
        "comfyui_workflow_runs",
        "comfyui_lora_models",
    ]

    def __init__(self, config: AuthConfig):
        """
        Initialize database validation service.

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
                self.db_url, min_size=1, max_size=5, command_timeout=30
            )
            logger.info("Created database validation connection pool")

        return self._pool

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed database validation connection pool")

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """,
                table_name,
            )

        return exists

    async def validate_core_tables(self) -> tuple[bool, list[str]]:
        """
        Validate that all core tables exist.

        Returns:
            Tuple of (all_exist: bool, missing_tables: list[str])
        """
        missing = []

        for table in self.CORE_TABLES:
            if not await self.table_exists(table):
                missing.append(table)
                logger.error(f"Core table '{table}' is missing from database")

        for table in self.OPTIONAL_TABLES:
            if not await self.table_exists(table):
                logger.warning(f"Optional table '{table}' is missing from database")

        return len(missing) == 0, missing

    async def apply_migration(self, migration_file: Path) -> bool:
        """
        Apply a SQL migration file to the database.

        Args:
            migration_file: Path to the SQL migration file

        Returns:
            True if migration was applied successfully, False otherwise
        """
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False

        try:
            sql_content = migration_file.read_text(encoding="utf-8")
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                # Execute migration in a transaction
                async with conn.transaction():
                    await conn.execute(sql_content)
                    logger.info(f"Applied migration: {migration_file.name}")

            return True
        except Exception:
            logger.exception("Failed to apply migration {migration_file.name}")
            return False

    async def apply_all_migrations(self, migrations_dir: Path) -> tuple[bool, list[str]]:
        """
        Apply all migrations in order from the migrations directory.

        Args:
            migrations_dir: Path to directory containing migration files

        Returns:
            Tuple of (all_succeeded: bool, applied_migrations: list[str])
        """
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return False, []

        # Get all SQL files sorted by name (ensures order)
        migration_files = sorted(migrations_dir.glob("*.sql"))
        applied = []

        for migration_file in migration_files:
            # Skip README files
            if migration_file.name.startswith("README"):
                continue

            if await self.apply_migration(migration_file):
                applied.append(migration_file.name)
            else:
                logger.error(f"Failed to apply migration: {migration_file.name}")
                return False, applied

        return True, applied

    async def validate_and_migrate(
        self, migrations_dir: Path | None = None
    ) -> tuple[bool, list[str]]:
        """
        Validate core tables exist and apply migrations if needed.

        This method:
        1. Validates core tables exist
        2. If missing, attempts to apply migrations from migrations_dir
        3. Re-validates after migration

        Args:
            migrations_dir: Optional path to migrations directory.
                          If None, uses default path relative to project root.

        Returns:
            Tuple of (success: bool, applied_migrations: list[str])
        """
        # Validate core tables
        all_exist, missing = await self.validate_core_tables()

        if all_exist:
            logger.info("All core database tables exist")
            return True, []

        logger.warning(f"Missing core tables: {missing}")

        # If migrations directory not provided, use default
        if migrations_dir is None:
            # Default to 01-data/supabase/migrations relative to project root
            # Path from: 04-lambda/server/projects/auth/services/database_validation_service.py
            # To: 01-data/supabase/migrations
            current_file = Path(__file__)
            # Go up: services -> auth -> projects -> server -> 04-lambda -> project root
            project_root = current_file.parent.parent.parent.parent.parent.parent
            migrations_dir = project_root / "01-data" / "supabase" / "migrations"

        # Apply migrations
        logger.info(f"Applying migrations from: {migrations_dir}")
        success, applied = await self.apply_all_migrations(migrations_dir)

        if not success:
            logger.error("Failed to apply all migrations")
            return False, applied

        # Re-validate after migration
        all_exist, still_missing = await self.validate_core_tables()

        if not all_exist:
            logger.error(
                f"Core tables still missing after migration: {still_missing}. "
                "Please check migration files and database permissions."
            )
            return False, applied

        logger.info("All core tables exist after migration")
        return True, applied
