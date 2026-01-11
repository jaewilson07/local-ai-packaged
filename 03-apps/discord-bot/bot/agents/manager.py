"""Agent manager for multi-agent system coordination."""

import logging
from typing import Optional

from bot.agents.base import BaseAgent
from bot.agents.discord_comm import DiscordCommunicationLayer

logger = logging.getLogger(__name__)

# Global agent manager instance
_agent_manager: Optional["AgentManager"] = None


class AgentManager:
    """Manages all agents in the multi-agent system.

    Responsibilities:
    - Register and unregister agents
    - Route tasks to appropriate agents
    - Manage agent lifecycle
    - Coordinate agent communication
    """

    def __init__(self):
        """Initialize agent manager."""
        self._agents: dict[str, BaseAgent] = {}
        self._discord_comm = DiscordCommunicationLayer()
        logger.info("Agent manager initialized")

    def set_discord_client(self, client) -> None:
        """Set Discord client for communication layer.

        Args:
            client: Discord client instance
        """
        self._discord_comm.set_client(client)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager.

        Args:
            agent: Agent instance to register
        """
        if agent.agent_id in self._agents:
            logger.warning(f"Agent {agent.agent_id} already registered, overwriting")

        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            logger.info(f"Unregistered agent: {agent_id} ({agent.name})")
        else:
            logger.warning(f"Agent {agent_id} not found for unregistration")

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """Get an agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance, or None if not found
        """
        return self._agents.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        """List all registered agents.

        Returns:
            List of agent instances
        """
        return list(self._agents.values())

    def find_agent_by_name(self, name: str) -> BaseAgent | None:
        """Find an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent instance, or None if not found
        """
        for agent in self._agents.values():
            if agent.name.lower() == name.lower():
                return agent
        return None

    async def start_agent(self, agent_id: str) -> bool:
        """Start an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if started successfully, False otherwise
        """
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return False

        try:
            await agent.start()
            return True
        except Exception as e:
            logger.exception(f"Failed to start agent {agent_id}: {e}")
            return False

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if stopped successfully, False otherwise
        """
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return False

        try:
            await agent.stop()
            return True
        except Exception as e:
            logger.exception(f"Failed to stop agent {agent_id}: {e}")
            return False

    async def start_all_agents(self) -> None:
        """Start all registered agents."""
        for agent_id in list(self._agents.keys()):
            await self.start_agent(agent_id)

    async def stop_all_agents(self) -> None:
        """Stop all registered agents."""
        for agent_id in list(self._agents.keys()):
            await self.stop_agent(agent_id)

    async def route_task(self, agent_id: str, task: dict) -> dict:
        """Route a task to a specific agent.

        Args:
            agent_id: Agent identifier
            task: Task dictionary

        Returns:
            Task result dictionary
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        if not agent.is_running:
            raise RuntimeError(f"Agent {agent_id} is not running")

        # Enqueue task
        await agent.enqueue_task(task)

        # Return acknowledgment (actual result will be processed asynchronously)
        return {
            "success": True,
            "agent_id": agent_id,
            "message": f"Task enqueued for agent {agent_id}",
        }

    def get_discord_comm(self) -> DiscordCommunicationLayer:
        """Get the Discord communication layer.

        Returns:
            Discord communication layer instance
        """
        return self._discord_comm

    def get_agent_status(self) -> dict[str, dict]:
        """Get status of all agents.

        Returns:
            Dictionary mapping agent IDs to their status dictionaries
        """
        return {agent_id: agent.to_dict() for agent_id, agent in self._agents.items()}


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance.

    Returns:
        Agent manager instance
    """
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager
