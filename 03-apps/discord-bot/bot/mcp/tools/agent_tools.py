"""Agent management MCP tools."""

import logging
from typing import List, Dict, Any, Optional
from bot.mcp.server import mcp
from bot.agents import get_agent_manager

logger = logging.getLogger(__name__)


@mcp.tool
async def list_agents() -> List[Dict[str, Any]]:
    """
    List all registered agents in the multi-agent system.
    
    Returns:
        List of agent information dictionaries.
    """
    manager = get_agent_manager()
    agents = manager.list_agents()
    return [agent.to_dict() for agent in agents]


@mcp.tool
async def get_agent_info(agent_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_id: The agent identifier.
    
    Returns:
        Dictionary containing agent information.
    """
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    return agent.to_dict()


@mcp.tool
async def start_agent(agent_id: str) -> Dict[str, Any]:
    """
    Start an agent.
    
    Args:
        agent_id: The agent identifier to start.
    
    Returns:
        Dictionary with success status.
    """
    manager = get_agent_manager()
    success = await manager.start_agent(agent_id)
    if not success:
        raise RuntimeError(f"Failed to start agent {agent_id}")
    return {
        "success": True,
        "agent_id": agent_id,
        "message": f"Agent {agent_id} started",
    }


@mcp.tool
async def stop_agent(agent_id: str) -> Dict[str, Any]:
    """
    Stop an agent.
    
    Args:
        agent_id: The agent identifier to stop.
    
    Returns:
        Dictionary with success status.
    """
    manager = get_agent_manager()
    success = await manager.stop_agent(agent_id)
    if not success:
        raise RuntimeError(f"Failed to stop agent {agent_id}")
    return {
        "success": True,
        "agent_id": agent_id,
        "message": f"Agent {agent_id} stopped",
    }


@mcp.tool
async def route_task_to_agent(agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route a task to a specific agent.
    
    Args:
        agent_id: The agent identifier to route the task to.
        task: Task dictionary with task-specific data.
    
    Returns:
        Dictionary with task routing result.
    """
    manager = get_agent_manager()
    return await manager.route_task(agent_id, task)


@mcp.tool
async def get_agent_status() -> Dict[str, Dict[str, Any]]:
    """
    Get status of all agents.
    
    Returns:
        Dictionary mapping agent IDs to their status dictionaries.
    """
    manager = get_agent_manager()
    return manager.get_agent_status()
