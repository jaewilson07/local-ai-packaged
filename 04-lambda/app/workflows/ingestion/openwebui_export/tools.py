"""OpenWebUI export tools for Pydantic AI agents.

This module provides tools for exporting Open WebUI conversations
to MongoDB RAG.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_deps(ctx: Any):
    """Extract dependencies from context."""
    deps = getattr(ctx, "deps", ctx)
    if hasattr(deps, "_deps"):
        deps = deps._deps
    return deps


async def get_conversations(
    ctx: Any,
    limit: int = 20,
    skip: int = 0,
) -> str:
    """
    Get a list of conversations from Open WebUI.

    Args:
        ctx: Context with dependencies
        limit: Maximum number of conversations to return
        skip: Number of conversations to skip

    Returns:
        String listing conversations
    """
    deps = _get_deps(ctx)
    http_client = getattr(deps, "http_client", None)

    if not http_client:
        return "[Not Configured] Open WebUI client not initialized"

    try:
        response = await http_client.get(
            "/api/v1/chats",
            params={"limit": limit, "skip": skip},
        )
        response.raise_for_status()
        data = response.json()

        conversations = data if isinstance(data, list) else data.get("chats", [])
        if not conversations:
            return "No conversations found"

        lines = [f"Found {len(conversations)} conversation(s):"]
        for conv in conversations:
            conv_id = conv.get("id", "unknown")
            title = conv.get("title", "Untitled")
            created = conv.get("created_at", "unknown")
            lines.append(f"  - [{conv_id}] {title} (created: {created})")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error getting conversations")
        return f"[Error] Failed to get conversations: {e}"


async def get_conversation(ctx: Any, conversation_id: str) -> str:
    """
    Get a single conversation with its messages.

    Args:
        ctx: Context with dependencies
        conversation_id: ID of the conversation to retrieve

    Returns:
        String with conversation details
    """
    deps = _get_deps(ctx)
    http_client = getattr(deps, "http_client", None)

    if not http_client:
        return "[Not Configured] Open WebUI client not initialized"

    try:
        response = await http_client.get(f"/api/v1/chats/{conversation_id}")
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "Untitled")
        messages = data.get("chat", {}).get("messages", [])

        lines = [f"Conversation: {title} (ID: {conversation_id})", f"Messages: {len(messages)}"]

        for msg in messages[:10]:  # Limit output
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            lines.append(f"\n[{role}]: {content}...")

        if len(messages) > 10:
            lines.append(f"\n... and {len(messages) - 10} more messages")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error getting conversation")
        return f"[Error] Failed to get conversation: {e}"


async def export_conversation(
    ctx: Any,
    conversation_id: str,
    include_metadata: bool = True,
) -> str:
    """
    Export a conversation to MongoDB RAG.

    Args:
        ctx: Context with dependencies
        conversation_id: ID of the conversation to export
        include_metadata: Whether to include conversation metadata

    Returns:
        String confirming export
    """
    deps = _get_deps(ctx)
    http_client = getattr(deps, "http_client", None)
    db = getattr(deps, "db", None)

    if not http_client:
        return "[Not Configured] Open WebUI client not initialized"

    if not db:
        return "[Not Configured] MongoDB not initialized"

    try:
        # Get the conversation
        response = await http_client.get(f"/api/v1/chats/{conversation_id}")
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "Untitled")
        chat = data.get("chat", {})
        messages = chat.get("messages", [])

        # Build export document
        export_doc = {
            "conversation_id": conversation_id,
            "title": title,
            "messages": messages,
            "message_count": len(messages),
        }

        if include_metadata:
            export_doc["metadata"] = {
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "models": chat.get("models", []),
                "tags": data.get("tags", []),
            }

        # Store in MongoDB
        collection = db["openwebui_exports"]
        await collection.update_one(
            {"conversation_id": conversation_id},
            {"$set": export_doc},
            upsert=True,
        )

        return f"Exported conversation '{title}' ({len(messages)} messages) to MongoDB"

    except Exception as e:
        logger.exception("Error exporting conversation")
        return f"[Error] Failed to export conversation: {e}"


__all__ = [
    "export_conversation",
    "get_conversation",
    "get_conversations",
]
