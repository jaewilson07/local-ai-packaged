"""Bluesky agent for social media integration."""

import asyncio
import logging
from typing import Any

from atproto import Client

from bot.agents.base import BaseAgent
from bot.agents.discord_comm import DiscordCommunicationLayer
from bot.config import config

logger = logging.getLogger(__name__)


class BlueskyAgent(BaseAgent):
    """Agent for Bluesky social media operations.

    Capabilities:
    - Post text to Bluesky
    - Repost (repost) Bluesky posts
    - Like posts
    - Follow users
    - Sync content between Discord and Bluesky
    """

    def __init__(
        self,
        agent_id: str = "bluesky",
        name: str = "Bluesky Agent",
        description: str = "Agent for Bluesky social media operations",
        discord_channel_id: str | None = None,
        bluesky_handle: str | None = None,
        bluesky_password: str | None = None,
    ):
        """Initialize Bluesky agent.

        Args:
            agent_id: Unique identifier
            name: Human-readable name
            description: Agent description
            discord_channel_id: Discord channel for communication
            bluesky_handle: Bluesky handle (e.g., "user.bsky.social")
            bluesky_password: Bluesky app password
        """
        super().__init__(agent_id, name, description, discord_channel_id)
        self.bluesky_handle = bluesky_handle or getattr(config, "BLUESKY_HANDLE", None)
        self.bluesky_password = bluesky_password or getattr(config, "BLUESKY_PASSWORD", None)
        self.client: Client | None = None
        self._discord_comm: DiscordCommunicationLayer | None = None

    def set_discord_comm(self, discord_comm: DiscordCommunicationLayer) -> None:
        """Set Discord communication layer.

        Args:
            discord_comm: Discord communication layer instance
        """
        self._discord_comm = discord_comm

    async def on_start(self) -> None:
        """Initialize Bluesky client."""
        if not self.bluesky_handle or not self.bluesky_password:
            logger.warning(f"Bluesky credentials not configured for agent {self.agent_id}")
            self.status_message = "Bluesky credentials not configured"
            return

        try:
            # Run synchronous Client operations in executor
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(None, lambda: Client())
            await loop.run_in_executor(
                None,
                lambda: self.client.login(
                    login=self.bluesky_handle,
                    password=self.bluesky_password,
                ),
            )
            self.status_message = f"Connected to Bluesky as {self.bluesky_handle}"
            logger.info(f"Bluesky agent {self.agent_id} connected to Bluesky")
        except Exception as e:
            logger.exception(f"Failed to connect to Bluesky: {e}")
            self.status = self.status.__class__.ERROR
            self.last_error = str(e)
            self.status_message = f"Failed to connect: {e}"

    async def on_stop(self) -> None:
        """Cleanup Bluesky client."""
        if self.client:
            # atproto Client doesn't have explicit logout, just clear reference
            self.client = None
            logger.info(f"Bluesky agent {self.agent_id} disconnected")

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Process a Bluesky task.

        Args:
            task: Task dictionary with 'action' and task-specific data

        Returns:
            Result dictionary
        """
        if not self.client:
            raise RuntimeError("Bluesky client not initialized")

        action = task.get("action")
        if not action:
            raise ValueError("Task must have an 'action' field")

        try:
            if action == "post":
                return await self._post_text(task)
            elif action == "repost":
                return await self._repost(task)
            elif action == "like":
                return await self._like(task)
            elif action == "follow":
                return await self._follow(task)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"Error processing Bluesky task: {e}")
            raise

    async def _post_text(self, task: dict[str, Any]) -> dict[str, Any]:
        """Post text to Bluesky.

        Args:
            task: Task with 'text' field

        Returns:
            Result dictionary with post URI
        """
        text = task.get("text")
        if not text:
            raise ValueError("Post task must have 'text' field")

        # Create post (run in executor since client is synchronous)
        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(None, lambda: self.client.send_post(text=text))

        result = {
            "success": True,
            "action": "post",
            "uri": post.uri,
            "cid": post.cid,
            "text": text,
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

    async def _repost(self, task: dict[str, Any]) -> dict[str, Any]:
        """Repost a Bluesky post.

        Args:
            task: Task with 'uri' field (Bluesky post URI)

        Returns:
            Result dictionary
        """
        uri = task.get("uri")
        if not uri:
            raise ValueError("Repost task must have 'uri' field")

        # Create repost (run in executor since client is synchronous)
        loop = asyncio.get_event_loop()
        repost = await loop.run_in_executor(None, lambda: self.client.send_repost(uri=uri))

        result = {
            "success": True,
            "action": "repost",
            "uri": repost.uri,
            "cid": repost.cid,
            "original_uri": uri,
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

    async def _like(self, task: dict[str, Any]) -> dict[str, Any]:
        """Like a Bluesky post.

        Args:
            task: Task with 'uri' field (Bluesky post URI)

        Returns:
            Result dictionary
        """
        uri = task.get("uri")
        if not uri:
            raise ValueError("Like task must have 'uri' field")

        # Create like (run in executor since client is synchronous)
        loop = asyncio.get_event_loop()
        like = await loop.run_in_executor(None, lambda: self.client.like(uri=uri))

        result = {
            "success": True,
            "action": "like",
            "uri": like.uri,
            "cid": like.cid,
            "subject_uri": uri,
        }

        return result

    async def _follow(self, task: dict[str, Any]) -> dict[str, Any]:
        """Follow a Bluesky user.

        Args:
            task: Task with 'did' field (Bluesky user DID)

        Returns:
            Result dictionary
        """
        did = task.get("did")
        if not did:
            raise ValueError("Follow task must have 'did' field")

        # Create follow (run in executor since client is synchronous)
        loop = asyncio.get_event_loop()
        follow = await loop.run_in_executor(None, lambda: self.client.follow(did=did))

        result = {
            "success": True,
            "action": "follow",
            "uri": follow.uri,
            "cid": follow.cid,
            "did": did,
        }

        return result
