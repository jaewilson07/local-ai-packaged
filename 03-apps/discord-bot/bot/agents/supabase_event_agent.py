"""Supabase event agent for event management integration."""

import logging
from typing import Any

import asyncpg

from bot.agents.base import BaseAgent
from bot.agents.discord_comm import DiscordCommunicationLayer
from bot.config import config
from bot.mcp.server import get_discord_client

logger = logging.getLogger(__name__)


class SupabaseEventAgent(BaseAgent):
    """Agent for managing events with Supabase integration.

    Capabilities:
    - Create events in Supabase
    - Sync events between Supabase and Discord
    - Manage event notifications
    - Query events from Supabase
    """

    def __init__(
        self,
        agent_id: str = "supabase-event",
        name: str = "Supabase Event Agent",
        description: str = "Agent for event management with Supabase integration",
        discord_channel_id: str | None = None,
        db_url: str | None = None,
    ):
        """Initialize Supabase event agent.

        Args:
            agent_id: Unique identifier
            name: Human-readable name
            description: Agent description
            discord_channel_id: Discord channel for communication
            db_url: Supabase database connection URL
        """
        super().__init__(agent_id, name, description, discord_channel_id)
        self.db_url = db_url or config.SUPABASE_DB_URL
        self.pool: asyncpg.Pool | None = None
        self._discord_comm: DiscordCommunicationLayer | None = None

    def set_discord_comm(self, discord_comm: DiscordCommunicationLayer) -> None:
        """Set Discord communication layer.

        Args:
            discord_comm: Discord communication layer instance
        """
        self._discord_comm = discord_comm

    async def on_start(self) -> None:
        """Initialize Supabase database connection."""
        if not self.db_url:
            logger.warning(f"Supabase database URL not configured for agent {self.agent_id}")
            self.status_message = "Supabase database URL not configured"
            return

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=5,
            )

            # Ensure events table exists
            await self._ensure_events_table()

            self.status_message = "Connected to Supabase database"
            logger.info(f"Supabase event agent {self.agent_id} connected to database")
        except Exception as e:
            logger.exception("Failed to connect to Supabase")
            self.status = self.status.__class__.ERROR
            self.last_error = str(e)
            self.status_message = f"Failed to connect: {e}"

    async def on_stop(self) -> None:
        """Cleanup database connection."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info(f"Supabase event agent {self.agent_id} disconnected")

    async def _ensure_events_table(self) -> None:
        """Ensure the events table exists in Supabase."""
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discord_events (
                    id SERIAL PRIMARY KEY,
                    discord_event_id BIGINT,
                    server_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    location TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    synced_to_discord BOOLEAN DEFAULT FALSE
                )
            """
            )

            # Create index on discord_event_id for faster lookups
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_discord_events_discord_event_id
                ON discord_events(discord_event_id)
            """
            )

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Process an event management task.

        Args:
            task: Task dictionary with 'action' and task-specific data

        Returns:
            Result dictionary
        """
        if not self.pool:
            raise RuntimeError("Database connection not initialized")

        action = task.get("action")
        if not action:
            raise ValueError("Task must have an 'action' field")

        try:
            if action == "create_event":
                return await self._create_event(task)
            if action == "sync_to_discord":
                return await self._sync_to_discord(task)
            if action == "list_events":
                return await self._list_events(task)
            if action == "get_event":
                return await self._get_event(task)
            raise ValueError(f"Unknown action: {action}")
        except Exception:
            logger.exception("Error processing event task")
            raise

    async def _create_event(self, task: dict[str, Any]) -> dict[str, Any]:
        """Create an event in Supabase.

        Args:
            task: Task with event data (name, description, start_time, etc.)

        Returns:
            Result dictionary with created event
        """
        server_id = task.get("server_id")
        name = task.get("name")
        start_time = task.get("start_time")

        if not server_id or not name or not start_time:
            raise ValueError(
                "Create event task must have 'server_id', 'name', and 'start_time' fields"
            )

        async with self.pool.acquire() as conn:
            event_id = await conn.fetchval(
                """
                INSERT INTO discord_events (
                    server_id, name, description, start_time, end_time, location
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """,
                int(server_id),
                name,
                task.get("description"),
                start_time,
                task.get("end_time"),
                task.get("location"),
            )

            # Fetch created event
            event = await conn.fetchrow(
                """
                SELECT * FROM discord_events WHERE id = $1
            """,
                event_id,
            )

        result = {
            "success": True,
            "action": "create_event",
            "event_id": event_id,
            "event": dict(event) if event else None,
        }

        # Send status update to Discord if configured
        if self.discord_channel_id and self._discord_comm:
            await self._discord_comm.send_task_result(
                self.discord_channel_id,
                self.agent_id,
                self.name,
                task.get("task_id", "unknown"),
                result,
                success=True,
            )

        return result

    async def _sync_to_discord(self, task: dict[str, Any]) -> dict[str, Any]:
        """Sync an event from Supabase to Discord.

        Args:
            task: Task with 'event_id' field

        Returns:
            Result dictionary with Discord event information
        """
        event_id = task.get("event_id")
        if not event_id:
            raise ValueError("Sync to Discord task must have 'event_id' field")

        # Get event from database
        async with self.pool.acquire() as conn:
            event = await conn.fetchrow(
                """
                SELECT * FROM discord_events WHERE id = $1
            """,
                event_id,
            )

        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Get Discord client
        client = get_discord_client()
        guild = client.get_guild(int(event["server_id"]))
        if not guild:
            raise ValueError(f"Server {event['server_id']} not found")

        # Create Discord scheduled event
        discord_event = await guild.create_scheduled_event(
            name=event["name"],
            description=event.get("description"),
            start_time=event["start_time"],
            end_time=event.get("end_time"),
            location=event.get("location"),
        )

        # Update database with Discord event ID
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE discord_events
                SET discord_event_id = $1, synced_to_discord = TRUE, updated_at = NOW()
                WHERE id = $2
            """,
                discord_event.id,
                event_id,
            )

        result = {
            "success": True,
            "action": "sync_to_discord",
            "event_id": event_id,
            "discord_event_id": str(discord_event.id),
            "discord_event": {
                "id": str(discord_event.id),
                "name": discord_event.name,
                "start_time": discord_event.start_time.isoformat(),
            },
        }

        return result

    async def _list_events(self, task: dict[str, Any]) -> dict[str, Any]:
        """List events from Supabase.

        Args:
            task: Task with optional 'server_id' filter

        Returns:
            Result dictionary with list of events
        """
        server_id = task.get("server_id")

        async with self.pool.acquire() as conn:
            if server_id:
                events = await conn.fetch(
                    """
                    SELECT * FROM discord_events
                    WHERE server_id = $1
                    ORDER BY start_time ASC
                """,
                    int(server_id),
                )
            else:
                events = await conn.fetch(
                    """
                    SELECT * FROM discord_events
                    ORDER BY start_time ASC
                """
                )

        result = {
            "success": True,
            "action": "list_events",
            "events": [dict(event) for event in events],
            "count": len(events),
        }

        return result

    async def _get_event(self, task: dict[str, Any]) -> dict[str, Any]:
        """Get a specific event from Supabase.

        Args:
            task: Task with 'event_id' field

        Returns:
            Result dictionary with event information
        """
        event_id = task.get("event_id")
        if not event_id:
            raise ValueError("Get event task must have 'event_id' field")

        async with self.pool.acquire() as conn:
            event = await conn.fetchrow(
                """
                SELECT * FROM discord_events WHERE id = $1
            """,
                event_id,
            )

        if not event:
            raise ValueError(f"Event {event_id} not found")

        result = {
            "success": True,
            "action": "get_event",
            "event": dict(event),
        }

        return result
