"""Tumblr agent for social media integration."""

import logging
from typing import Any

import pytumblr

from bot.agents.base import BaseAgent
from bot.agents.discord_comm import DiscordCommunicationLayer
from bot.config import config

logger = logging.getLogger(__name__)


class TumblrAgent(BaseAgent):
    """Agent for Tumblr social media operations.

    Capabilities:
    - Repost Tumblr posts
    - Share URLs to Tumblr
    - Extract URLs from Tumblr posts
    - Post text/images to Tumblr
    """

    def __init__(
        self,
        agent_id: str = "tumblr",
        name: str = "Tumblr Agent",
        description: str = "Agent for Tumblr social media operations",
        discord_channel_id: str | None = None,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        oauth_token: str | None = None,
        oauth_secret: str | None = None,
    ):
        """Initialize Tumblr agent.

        Args:
            agent_id: Unique identifier
            name: Human-readable name
            description: Agent description
            discord_channel_id: Discord channel for communication
            consumer_key: Tumblr OAuth consumer key
            consumer_secret: Tumblr OAuth consumer secret
            oauth_token: Tumblr OAuth token
            oauth_secret: Tumblr OAuth secret
        """
        super().__init__(agent_id, name, description, discord_channel_id)
        self.consumer_key = consumer_key or config.TUMBLR_CONSUMER_KEY
        self.consumer_secret = consumer_secret or config.TUMBLR_CONSUMER_SECRET
        self.oauth_token = oauth_token or config.TUMBLR_OAUTH_TOKEN
        self.oauth_secret = oauth_secret or config.TUMBLR_OAUTH_SECRET
        self.client: pytumblr.TumblrRestClient | None = None
        self._discord_comm: DiscordCommunicationLayer | None = None

    def set_discord_comm(self, discord_comm: DiscordCommunicationLayer) -> None:
        """Set Discord communication layer.

        Args:
            discord_comm: Discord communication layer instance
        """
        self._discord_comm = discord_comm

    async def on_start(self) -> None:
        """Initialize Tumblr client."""
        if not all([self.consumer_key, self.consumer_secret, self.oauth_token, self.oauth_secret]):
            logger.warning(f"Tumblr credentials not fully configured for agent {self.agent_id}")
            self.status_message = "Tumblr credentials not fully configured"
            return

        try:
            self.client = pytumblr.TumblrRestClient(
                self.consumer_key,
                self.consumer_secret,
                self.oauth_token,
                self.oauth_secret,
            )
            # Test connection by getting user info
            user_info = self.client.info()
            self.status_message = (
                f"Connected to Tumblr as {user_info.get('user', {}).get('name', 'unknown')}"
            )
            logger.info(f"Tumblr agent {self.agent_id} connected to Tumblr")
        except Exception as e:
            logger.exception(f"Failed to connect to Tumblr: {e}")
            self.status = self.status.__class__.ERROR
            self.last_error = str(e)
            self.status_message = f"Failed to connect: {e}"

    async def on_stop(self) -> None:
        """Cleanup Tumblr client."""
        self.client = None
        logger.info(f"Tumblr agent {self.agent_id} disconnected")

    async def process_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Process a Tumblr task.

        Args:
            task: Task dictionary with 'action' and task-specific data

        Returns:
            Result dictionary
        """
        if not self.client:
            raise RuntimeError("Tumblr client not initialized")

        action = task.get("action")
        if not action:
            raise ValueError("Task must have an 'action' field")

        try:
            if action == "repost":
                return await self._repost(task)
            elif action == "share_url":
                return await self._share_url(task)
            elif action == "post_text":
                return await self._post_text(task)
            elif action == "extract_urls":
                return await self._extract_urls(task)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"Error processing Tumblr task: {e}")
            raise

    async def _repost(self, task: dict[str, Any]) -> dict[str, Any]:
        """Repost a Tumblr post.

        Args:
            task: Task with 'blog_name' and 'post_id' fields

        Returns:
            Result dictionary
        """
        blog_name = task.get("blog_name")
        post_id = task.get("post_id")
        if not blog_name or not post_id:
            raise ValueError("Repost task must have 'blog_name' and 'post_id' fields")

        # Reblog the post
        result = self.client.reblog(blog_name, id=post_id)

        response = {
            "success": True,
            "action": "repost",
            "blog_name": blog_name,
            "post_id": post_id,
            "result": result,
        }

        # Send status update to Discord if configured
        if self.discord_channel_id and self._discord_comm:
            await self._discord_comm.send_task_result(
                self.discord_channel_id,
                self.agent_id,
                self.name,
                task.get("task_id", "unknown"),
                response,
                success=True,
            )

        return response

    async def _share_url(self, task: dict[str, Any]) -> dict[str, Any]:
        """Share a URL to Tumblr.

        Args:
            task: Task with 'blog_name', 'url', and optional 'comment' fields

        Returns:
            Result dictionary
        """
        blog_name = task.get("blog_name")
        url = task.get("url")
        comment = task.get("comment", "")

        if not blog_name or not url:
            raise ValueError("Share URL task must have 'blog_name' and 'url' fields")

        # Create a link post
        result = self.client.create_link(
            blog_name,
            url=url,
            description=comment,
        )

        response = {
            "success": True,
            "action": "share_url",
            "blog_name": blog_name,
            "url": url,
            "comment": comment,
            "result": result,
        }

        # Send status update to Discord if configured
        if self.discord_channel_id and self._discord_comm:
            await self._discord_comm.send_task_result(
                self.discord_channel_id,
                self.agent_id,
                self.name,
                task.get("task_id", "unknown"),
                response,
                success=True,
            )

        return response

    async def _post_text(self, task: dict[str, Any]) -> dict[str, Any]:
        """Post text to Tumblr.

        Args:
            task: Task with 'blog_name' and 'text' fields

        Returns:
            Result dictionary
        """
        blog_name = task.get("blog_name")
        text = task.get("text")

        if not blog_name or not text:
            raise ValueError("Post text task must have 'blog_name' and 'text' fields")

        # Create a text post
        result = self.client.create_text(blog_name, body=text)

        response = {
            "success": True,
            "action": "post_text",
            "blog_name": blog_name,
            "text": text,
            "result": result,
        }

        return response

    async def _extract_urls(self, task: dict[str, Any]) -> dict[str, Any]:
        """Extract URLs from a Tumblr post.

        Args:
            task: Task with 'blog_name' and 'post_id' fields

        Returns:
            Result dictionary with extracted URLs
        """
        blog_name = task.get("blog_name")
        post_id = task.get("post_id")

        if not blog_name or not post_id:
            raise ValueError("Extract URLs task must have 'blog_name' and 'post_id' fields")

        # Get post information
        post = self.client.posts(blog_name, id=post_id)

        # Extract URLs from post (this is a simplified version)
        urls = []
        if post and "posts" in post and len(post["posts"]) > 0:
            post_data = post["posts"][0]
            # Extract URLs from various fields
            if "url" in post_data:
                urls.append(post_data["url"])
            if "source_url" in post_data:
                urls.append(post_data["source_url"])
            # Extract URLs from body text (simplified)
            if "body" in post_data:
                import re

                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls.extend(re.findall(url_pattern, post_data["body"]))

        response = {
            "success": True,
            "action": "extract_urls",
            "blog_name": blog_name,
            "post_id": post_id,
            "urls": list(set(urls)),  # Remove duplicates
        }

        return response
