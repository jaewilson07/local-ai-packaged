"""N8n workflow tools for Pydantic AI agents.

This module provides tools for managing N8n workflows through the N8n API.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_http_client(ctx: Any):
    """Extract HTTP client from context."""
    deps = getattr(ctx, "deps", ctx)
    if hasattr(deps, "_deps"):
        deps = deps._deps
    return getattr(deps, "http_client", None)


async def create_workflow(
    ctx: Any,
    name: str,
    nodes: list[dict[str, Any]] | None = None,
    connections: dict[str, list[dict[str, Any]]] | None = None,
    active: bool = False,
    settings: dict[str, Any] | None = None,
) -> str:
    """
    Create a new N8n workflow.

    Args:
        ctx: Context with dependencies (must have http_client)
        name: Workflow name
        nodes: List of workflow nodes
        connections: Node connections mapping
        active: Whether to activate the workflow
        settings: Workflow settings

    Returns:
        String describing the result
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        payload = {
            "name": name,
            "nodes": nodes or [],
            "connections": connections or {},
            "active": active,
            "settings": settings or {},
        }

        response = await client.post("/workflows", json=payload)
        response.raise_for_status()
        data = response.json()

        workflow_id = data.get("id", "unknown")
        return f"Created workflow '{name}' (ID: {workflow_id})"

    except Exception as e:
        logger.exception("Error creating workflow")
        return f"[Error] Failed to create workflow: {e}"


async def update_workflow(
    ctx: Any,
    workflow_id: str,
    name: str | None = None,
    nodes: list[dict[str, Any]] | None = None,
    connections: dict[str, list[dict[str, Any]]] | None = None,
    active: bool | None = None,
    settings: dict[str, Any] | None = None,
) -> str:
    """
    Update an existing N8n workflow.

    Args:
        ctx: Context with dependencies
        workflow_id: Workflow ID to update
        name: New workflow name (optional)
        nodes: New workflow nodes (optional)
        connections: New node connections (optional)
        active: New active state (optional)
        settings: New settings (optional)

    Returns:
        String describing the result
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        # First get existing workflow
        response = await client.get(f"/workflows/{workflow_id}")
        response.raise_for_status()
        existing = response.json()

        # Update only provided fields
        if name is not None:
            existing["name"] = name
        if nodes is not None:
            existing["nodes"] = nodes
        if connections is not None:
            existing["connections"] = connections
        if active is not None:
            existing["active"] = active
        if settings is not None:
            existing["settings"] = settings

        # Remove fields that shouldn't be updated
        existing.pop("id", None)
        existing.pop("createdAt", None)
        existing.pop("updatedAt", None)

        response = await client.put(f"/workflows/{workflow_id}", json=existing)
        response.raise_for_status()

        return f"Updated workflow (ID: {workflow_id})"

    except Exception as e:
        logger.exception("Error updating workflow")
        return f"[Error] Failed to update workflow: {e}"


async def delete_workflow(ctx: Any, workflow_id: str) -> str:
    """
    Delete an N8n workflow.

    Args:
        ctx: Context with dependencies
        workflow_id: Workflow ID to delete

    Returns:
        String describing the result
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        response = await client.delete(f"/workflows/{workflow_id}")
        response.raise_for_status()

        return f"Deleted workflow (ID: {workflow_id})"

    except Exception as e:
        logger.exception("Error deleting workflow")
        return f"[Error] Failed to delete workflow: {e}"


async def activate_workflow(ctx: Any, workflow_id: str, active: bool) -> str:
    """
    Activate or deactivate an N8n workflow.

    Args:
        ctx: Context with dependencies
        workflow_id: Workflow ID
        active: True to activate, False to deactivate

    Returns:
        String describing the result
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        endpoint = f"/workflows/{workflow_id}/{'activate' if active else 'deactivate'}"
        response = await client.post(endpoint)
        response.raise_for_status()

        status = "activated" if active else "deactivated"
        return f"Workflow {status} (ID: {workflow_id})"

    except Exception as e:
        logger.exception("Error activating/deactivating workflow")
        return f"[Error] Failed to change workflow state: {e}"


async def list_workflows(ctx: Any, active_only: bool = False) -> str:
    """
    List all N8n workflows.

    Args:
        ctx: Context with dependencies
        active_only: If True, only return active workflows

    Returns:
        String listing the workflows
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        params = {}
        if active_only:
            params["active"] = "true"

        response = await client.get("/workflows", params=params)
        response.raise_for_status()
        data = response.json()

        workflows = data.get("data", [])
        if not workflows:
            return "No workflows found"

        lines = [f"Found {len(workflows)} workflow(s):"]
        for wf in workflows:
            status = "active" if wf.get("active") else "inactive"
            lines.append(f"  - {wf.get('name', 'Unnamed')} (ID: {wf.get('id')}, {status})")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error listing workflows")
        return f"[Error] Failed to list workflows: {e}"


async def execute_workflow(
    ctx: Any, workflow_id: str, input_data: dict[str, Any] | None = None
) -> str:
    """
    Execute an N8n workflow.

    Args:
        ctx: Context with dependencies
        workflow_id: Workflow ID to execute
        input_data: Input data for the workflow (optional)

    Returns:
        String describing the execution result
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        payload = input_data or {}
        response = await client.post(f"/workflows/{workflow_id}/run", json=payload)
        response.raise_for_status()
        data = response.json()

        execution_id = data.get("executionId", "unknown")
        status = data.get("status", "unknown")
        return f"Workflow executed (Execution ID: {execution_id}, Status: {status})"

    except Exception as e:
        logger.exception("Error executing workflow")
        return f"[Error] Failed to execute workflow: {e}"


async def discover_n8n_nodes(ctx: Any, category: str | None = None) -> str:
    """
    Discover available N8n nodes via API.

    Args:
        ctx: Context with dependencies
        category: Optional category filter

    Returns:
        String listing available nodes
    """
    client = _get_http_client(ctx)
    if not client:
        return "[Not Configured] N8n API client not initialized"

    try:
        response = await client.get("/node-types")
        response.raise_for_status()
        data = response.json()

        nodes = data.get("data", [])
        if category:
            nodes = [
                n
                for n in nodes
                if category.lower() in n.get("group", [])
                or category.lower() in n.get("name", "").lower()
            ]

        if not nodes:
            return "No nodes found" + (f" for category '{category}'" if category else "")

        lines = [f"Found {len(nodes)} node type(s):"]
        for node in nodes[:20]:  # Limit output
            name = node.get("displayName", node.get("name", "Unknown"))
            description = node.get("description", "No description")[:80]
            lines.append(f"  - {name}: {description}")

        if len(nodes) > 20:
            lines.append(f"  ... and {len(nodes) - 20} more")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error discovering nodes")
        return f"[Error] Failed to discover nodes: {e}"


async def search_n8n_knowledge_base(
    ctx: Any,
    query: str,
    match_count: int | None = 5,
    search_type: str | None = "hybrid",
) -> str:
    """
    Search the knowledge base for N8n-related information.

    This is a placeholder - implement with actual RAG search when available.

    Args:
        ctx: Context with dependencies
        query: Search query
        match_count: Number of results
        search_type: Type of search

    Returns:
        String with search results
    """
    # TODO: Implement actual RAG search integration
    return f"[Not Implemented] Knowledge base search for: {query}"


async def search_node_examples(
    ctx: Any,
    node_type: str | None = None,
    query: str | None = None,
    match_count: int | None = 5,
) -> str:
    """
    Search for N8n node usage examples.

    This is a placeholder - implement with actual example search when available.

    Args:
        ctx: Context with dependencies
        node_type: Node type to filter by
        query: Search query
        match_count: Number of results

    Returns:
        String with example results
    """
    # TODO: Implement actual example search
    search_desc = node_type or query or "all nodes"
    return f"[Not Implemented] Node examples search for: {search_desc}"


__all__ = [
    "activate_workflow",
    "create_workflow",
    "delete_workflow",
    "discover_n8n_nodes",
    "execute_workflow",
    "list_workflows",
    "search_n8n_knowledge_base",
    "search_node_examples",
    "update_workflow",
]
