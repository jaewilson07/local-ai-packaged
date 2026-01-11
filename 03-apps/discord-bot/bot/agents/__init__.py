"""Multi-agent system for Discord bot.

This module provides the foundation for a multi-agent system where specialized
agents can coordinate via Discord channels and expose their capabilities through MCP tools.
"""

from .base import AgentMessage, AgentStatus, BaseAgent
from .discord_comm import DiscordCommunicationLayer
from .manager import AgentManager, get_agent_manager

__all__ = [
    "AgentManager",
    "AgentMessage",
    "AgentStatus",
    "BaseAgent",
    "DiscordCommunicationLayer",
    "get_agent_manager",
]
