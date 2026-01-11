"""Bluesky MCP tools."""

import logging
from typing import Any

from bot.agents import get_agent_manager
from bot.mcp.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def bluesky_post(text: str) -> dict[str, Any]:
    """
    Post text to Bluesky via the Bluesky agent.

    Args:
        text: The text content to post.

    Returns:
        Dictionary with post result including URI.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("bluesky")
    if not agent:
        raise RuntimeError("Bluesky agent not registered")

    if not agent.is_running:
        raise RuntimeError("Bluesky agent is not running")

    task = {
        "action": "post",
        "text": text,
        "task_id": f"post_{id(text)}",
    }

    return await agent.process_task(task)


@mcp.tool
async def bluesky_repost(uri: str) -> dict[str, Any]:
    """
    Repost a Bluesky post via the Bluesky agent.

    Args:
        uri: The Bluesky post URI to repost (e.g., "at://did:plc:.../app.bsky.feed.post/...").

    Returns:
        Dictionary with repost result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("bluesky")
    if not agent:
        raise RuntimeError("Bluesky agent not registered")

    if not agent.is_running:
        raise RuntimeError("Bluesky agent is not running")

    task = {
        "action": "repost",
        "uri": uri,
        "task_id": f"repost_{uri.split('/')[-1]}",
    }

    return await agent.process_task(task)


@mcp.tool
async def bluesky_like(uri: str) -> dict[str, Any]:
    """
    Like a Bluesky post via the Bluesky agent.

    Args:
        uri: The Bluesky post URI to like.

    Returns:
        Dictionary with like result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("bluesky")
    if not agent:
        raise RuntimeError("Bluesky agent not registered")

    if not agent.is_running:
        raise RuntimeError("Bluesky agent is not running")

    task = {
        "action": "like",
        "uri": uri,
        "task_id": f"like_{uri.split('/')[-1]}",
    }

    return await agent.process_task(task)


@mcp.tool
async def bluesky_follow(did: str) -> dict[str, Any]:
    """
    Follow a Bluesky user via the Bluesky agent.

    Args:
        did: The Bluesky user DID (Decentralized Identifier) to follow.

    Returns:
        Dictionary with follow result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("bluesky")
    if not agent:
        raise RuntimeError("Bluesky agent not registered")

    if not agent.is_running:
        raise RuntimeError("Bluesky agent is not running")

    task = {
        "action": "follow",
        "did": did,
        "task_id": f"follow_{did}",
    }

    return await agent.process_task(task)
