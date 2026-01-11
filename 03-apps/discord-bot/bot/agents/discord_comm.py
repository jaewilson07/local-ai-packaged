"""Discord communication layer for agents."""

import logging
from typing import Any

import discord

from .base import AgentMessage

logger = logging.getLogger(__name__)


class DiscordCommunicationLayer:
    """Handles communication between agents and Discord channels.

    Agents can post status updates, task assignments, and results to Discord channels.
    """

    def __init__(self):
        """Initialize Discord communication layer."""
        self._client: discord.Client | None = None

    def set_client(self, client: discord.Client) -> None:
        """Set the Discord client.

        Args:
            client: Discord client instance
        """
        self._client = client
        logger.info("Discord client set for communication layer")

    async def send_agent_message(
        self,
        channel_id: str,
        agent_id: str,
        agent_name: str,
        message: AgentMessage,
    ) -> discord.Message | None:
        """Send an agent message to a Discord channel.

        Args:
            channel_id: Discord channel ID
            agent_id: Agent identifier
            agent_name: Agent name
            message: Agent message to send

        Returns:
            Sent Discord message, or None if failed
        """
        if not self._client:
            logger.warning("Discord client not set, cannot send message")
            return None

        try:
            channel = self._client.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return None

            if not isinstance(channel, discord.TextChannel):
                logger.warning(f"Channel {channel_id} is not a text channel")
                return None

            # Format message based on type
            content = self._format_message(agent_id, agent_name, message)

            # Send message
            sent_message = await channel.send(content)
            logger.debug(f"Sent agent message from {agent_id} to channel {channel_id}")
            return sent_message

        except Exception as e:
            logger.exception(f"Failed to send agent message: {e}")
            return None

    async def send_status_update(
        self,
        channel_id: str,
        agent_id: str,
        agent_name: str,
        status: str,
        message: str | None = None,
    ) -> discord.Message | None:
        """Send a status update to a Discord channel.

        Args:
            channel_id: Discord channel ID
            agent_id: Agent identifier
            agent_name: Agent name
            status: Status string
            message: Optional status message

        Returns:
            Sent Discord message, or None if failed
        """
        agent_message = AgentMessage(
            agent_id=agent_id,
            message_type="status",
            content=message or f"Status: {status}",
            metadata={"status": status},
        )
        return await self.send_agent_message(channel_id, agent_id, agent_name, agent_message)

    async def send_task_result(
        self,
        channel_id: str,
        agent_id: str,
        agent_name: str,
        task_id: str,
        result: dict[str, Any],
        success: bool = True,
    ) -> discord.Message | None:
        """Send a task result to a Discord channel.

        Args:
            channel_id: Discord channel ID
            agent_id: Agent identifier
            agent_name: Agent name
            task_id: Task identifier
            result: Task result dictionary
            success: Whether task succeeded

        Returns:
            Sent Discord message, or None if failed
        """
        status_emoji = "✅" if success else "❌"
        content = f"{status_emoji} Task {task_id} {'completed' if success else 'failed'}"

        agent_message = AgentMessage(
            agent_id=agent_id,
            message_type="result",
            content=content,
            metadata={
                "task_id": task_id,
                "success": success,
                "result": result,
            },
        )
        return await self.send_agent_message(channel_id, agent_id, agent_name, agent_message)

    def _format_message(
        self,
        agent_id: str,
        agent_name: str,
        message: AgentMessage,
    ) -> str:
        """Format an agent message for Discord.

        Args:
            agent_id: Agent identifier
            agent_name: Agent name
            message: Agent message

        Returns:
            Formatted message string
        """
        # Format based on message type
        if message.message_type == "status":
            return f"**{agent_name}** ({agent_id}): {message.content}"
        elif message.message_type == "result":
            return f"**{agent_name}**: {message.content}"
        elif message.message_type == "error":
            return f"**{agent_name}** ❌ Error: {message.content}"
        elif message.message_type == "task":
            return f"**{agent_name}** 📋 Task: {message.content}"
        else:
            return f"**{agent_name}**: {message.content}"
