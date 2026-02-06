"""Database validation and migration service."""

import logging
from pathlib import Path

import asyncpg

from .config import SupabaseConfig
from .schemas import DatabaseMigrationResult, TableValidationResult

logger = logging.getLogger(__name__)


class DatabaseValidator:
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

    def __init__(self, config: SupabaseConfig):
        """
        Initialize database validator.

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
        """Check if a table exists in the database."""
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

    async def validate_core_tables(self) -> TableValidationResult:
        """
        Validate that all core tables exist.

        Returns:
            TableValidationResult with validation details
        """
        missing = []
        optional_missing = []

        for table in self.CORE_TABLES:
            if not await self.table_exists(table):
                missing.append(table)
                logger.error(f"Core table '{table}' is missing from database")

        for table in self.OPTIONAL_TABLES:
            if not await self.table_exists(table):
                optional_missing.append(table)
                logger.warning(f"Optional table '{table}' is missing from database")

        return TableValidationResult(
            all_exist=len(missing) == 0,
            missing_tables=missing,
            optional_missing=optional_missing,
        )

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
            logger.exception(f"Failed to apply migration {migration_file.name}")
            return False

    async def apply_all_migrations(self, migrations_dir: Path) -> DatabaseMigrationResult:
        """
        Apply all migrations in order from the migrations directory.

        Args:
            migrations_dir: Path to directory containing migration files

        Returns:
            DatabaseMigrationResult with migration details
        """
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return DatabaseMigrationResult(success=False)

        # Get all SQL files sorted by name (ensures order)
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            logger.info("No migrations found")
            return DatabaseMigrationResult(success=True)

        applied = []
        failed = []

        for migration_file in migration_files:
            if await self.apply_migration(migration_file):
                applied.append(migration_file.name)
            else:
                failed.append(migration_file.name)

        success = len(failed) == 0
        if success:
            logger.info(f"Applied {len(applied)} migrations successfully")
        else:
            logger.error(f"Failed to apply {len(failed)} migrations: {failed}")

        return DatabaseMigrationResult(
            success=success,
            applied_migrations=applied,
            failed_migrations=failed,
        )
