"""SQLite database operations for user mapping."""

from datetime import datetime

import aiosqlite

from bot.config import config


class Database:
    """Database manager for user mappings."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.BOT_DB_PATH

    async def initialize(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    immich_person_id TEXT NOT NULL,
                    notify_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS last_check (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    timestamp TIMESTAMP NOT NULL
                )
                """
            )
            await db.commit()

    async def get_user_by_discord_id(self, discord_id: str) -> dict | None:
        """Get user mapping by Discord ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_immich_person_id(self, immich_person_id: str) -> dict | None:
        """Get user mapping by Immich person ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE immich_person_id = ? AND notify_enabled = 1",
                (immich_person_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def save_user_mapping(
        self, discord_id: str, immich_person_id: str, notify_enabled: bool = True
    ) -> None:
        """Save or update user mapping."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO users (discord_id, immich_person_id, notify_enabled)
                VALUES (?, ?, ?)
                """,
                (discord_id, immich_person_id, 1 if notify_enabled else 0),
            )
            await db.commit()

    async def update_notify_enabled(self, discord_id: str, notify_enabled: bool) -> None:
        """Update notification preference for user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET notify_enabled = ? WHERE discord_id = ?",
                (1 if notify_enabled else 0, discord_id),
            )
            await db.commit()

    async def get_last_check_timestamp(self) -> datetime | None:
        """Get last notification check timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT timestamp FROM last_check WHERE id = 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
                return None

    async def update_last_check_timestamp(self, timestamp: datetime) -> None:
        """Update last notification check timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO last_check (id, timestamp)
                VALUES (1, ?)
                """,
                (timestamp.isoformat(),),
            )
            await db.commit()
