"""Tumblr MCP tools."""

import logging
from typing import Dict, Any
from bot.mcp.server import mcp
from bot.agents import get_agent_manager

logger = logging.getLogger(__name__)


@mcp.tool
async def tumblr_repost(blog_name: str, post_id: int) -> Dict[str, Any]:
    """
    Repost a Tumblr post via the Tumblr agent.
    
    Args:
        blog_name: The Tumblr blog name (e.g., "example.tumblr.com" or just "example").
        post_id: The ID of the post to repost.
    
    Returns:
        Dictionary with repost result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("tumblr")
    if not agent:
        raise RuntimeError("Tumblr agent not registered")
    
    if not agent.is_running:
        raise RuntimeError("Tumblr agent is not running")
    
    task = {
        "action": "repost",
        "blog_name": blog_name,
        "post_id": post_id,
        "task_id": f"repost_{post_id}",
    }
    
    return await agent.process_task(task)


@mcp.tool
async def tumblr_share_url(blog_name: str, url: str, comment: str = "") -> Dict[str, Any]:
    """
    Share a URL to Tumblr via the Tumblr agent.
    
    Args:
        blog_name: The Tumblr blog name to post to.
        url: The URL to share.
        comment: Optional comment/description for the link post.
    
    Returns:
        Dictionary with share result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("tumblr")
    if not agent:
        raise RuntimeError("Tumblr agent not registered")
    
    if not agent.is_running:
        raise RuntimeError("Tumblr agent is not running")
    
    task = {
        "action": "share_url",
        "blog_name": blog_name,
        "url": url,
        "comment": comment,
        "task_id": f"share_{id(url)}",
    }
    
    return await agent.process_task(task)


@mcp.tool
async def tumblr_post_text(blog_name: str, text: str) -> Dict[str, Any]:
    """
    Post text to Tumblr via the Tumblr agent.
    
    Args:
        blog_name: The Tumblr blog name to post to.
        text: The text content to post.
    
    Returns:
        Dictionary with post result.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("tumblr")
    if not agent:
        raise RuntimeError("Tumblr agent not registered")
    
    if not agent.is_running:
        raise RuntimeError("Tumblr agent is not running")
    
    task = {
        "action": "post_text",
        "blog_name": blog_name,
        "text": text,
        "task_id": f"post_{id(text)}",
    }
    
    return await agent.process_task(task)


@mcp.tool
async def tumblr_extract_urls(blog_name: str, post_id: int) -> Dict[str, Any]:
    """
    Extract URLs from a Tumblr post via the Tumblr agent.
    
    Args:
        blog_name: The Tumblr blog name.
        post_id: The ID of the post to extract URLs from.
    
    Returns:
        Dictionary with extracted URLs.
    """
    manager = get_agent_manager()
    agent = manager.get_agent("tumblr")
    if not agent:
        raise RuntimeError("Tumblr agent not registered")
    
    if not agent.is_running:
        raise RuntimeError("Tumblr agent is not running")
    
    task = {
        "action": "extract_urls",
        "blog_name": blog_name,
        "post_id": post_id,
        "task_id": f"extract_{post_id}",
    }
    
    return await agent.process_task(task)
