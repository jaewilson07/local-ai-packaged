"""Base agent class and types for multi-agent system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMessage:
    """Message structure for agent communication."""

    agent_id: str
    message_type: str  # "status", "result", "error", "task"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system.

    Agents are specialized workers that can:
    - Perform specific tasks (e.g., Bluesky posting, Tumblr reposting)
    - Communicate via Discord channels
    - Expose capabilities through MCP tools
    - Persist state in Supabase
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        discord_channel_id: str | None = None,
    ):
        """Initialize base agent.

        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name
            description: Agent description
            discord_channel_id: Optional Discord channel for agent communication
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.discord_channel_id = discord_channel_id
        self.status = AgentStatus.IDLE
        self.status_message: str | None = None
        self.last_error: str | None = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self._running and self.status == AgentStatus.RUNNING

    async def start(self) -> None:
        """Start the agent."""
        if self._running:
            logger.warning(f"Agent {self.agent_id} is already running")
            return

        self._running = True
        self.status = AgentStatus.RUNNING
        self.status_message = "Agent started"
        self.updated_at = datetime.utcnow()

        # Start agent task loop
        asyncio.create_task(self._run_loop())

        # Call agent-specific startup
        await self.on_start()

        logger.info(f"Agent {self.agent_id} ({self.name}) started")

    async def stop(self) -> None:
        """Stop the agent."""
        if not self._running:
            return

        self._running = False
        self.status = AgentStatus.STOPPED
        self.status_message = "Agent stopped"
        self.updated_at = datetime.utcnow()

        # Call agent-specific shutdown
        await self.on_stop()

        logger.info(f"Agent {self.agent_id} ({self.name}) stopped")

    async def _run_loop(self) -> None:
        """Main agent task loop."""
        while self._running:
            try:
                # Wait for task with timeout
                try:
                    task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                    await self.process_task(task)
                except asyncio.TimeoutError:
                    # No task, continue loop
                    continue
                except Exception as e:
                    logger.exception("Error processing task in agent {self.agent_id}")
                    self.status = AgentStatus.ERROR
                    self.last_error = str(e)
                    self.updated_at = datetime.utcnow()
            except Exception:
                logger.exception("Error in agent loop {self.agent_id}")
                await asyncio.sleep(1)

    async def enqueue_task(self, task: dict[str, Any]) -> None:
        """Enqueue a task for the agent to process.

        Args:
            task: Task dictionary with task-specific data
        """
        await self._task_queue.put(task)
        logger.debug(f"Task enqueued for agent {self.agent_id}")

    @abstractmethod
    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Process a task. Must be implemented by subclasses.

        Args:
            task: Task dictionary with task-specific data

        Returns:
            Result dictionary
        """

    @abstractmethod
    async def on_start(self) -> None:
        """Called when agent starts. Override for agent-specific initialization."""

    @abstractmethod
    async def on_stop(self) -> None:
        """Called when agent stops. Override for agent-specific cleanup."""

    def to_dict(self) -> dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "status_message": self.status_message,
            "last_error": self.last_error,
            "discord_channel_id": self.discord_channel_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
