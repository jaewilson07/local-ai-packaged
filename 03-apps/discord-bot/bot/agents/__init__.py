"""Multi-agent system for Discord bot.

This module provides the foundation for a multi-agent system where specialized
agents can coordinate via Discord channels and expose their capabilities through MCP tools.
"""

from .manager import AgentManager, get_agent_manager
from .base import BaseAgent, AgentStatus, AgentMessage
from .discord_comm import DiscordCommunicationLayer

__all__ = [
    "AgentManager",
    "get_agent_manager",
    "BaseAgent",
    "AgentStatus",
    "AgentMessage",
    "DiscordCommunicationLayer",
]
