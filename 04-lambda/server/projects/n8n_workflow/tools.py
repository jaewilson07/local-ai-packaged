"""Tools for N8n Workflow Agent."""

import logging
from typing import Optional, List, Dict, Any
from pydantic_ai import RunContext
from httpx import HTTPStatusError

from server.projects.shared.wrappers import DepsWrapper
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps

logger = logging.getLogger(__name__)


async def create_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    name: str,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    active: bool = False,
    settings: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new N8n workflow.
    
    Args:
        ctx: Agent runtime context with dependencies
        name: Workflow name
        nodes: List of workflow nodes (default: empty list)
        connections: Workflow connections (default: empty dict)
        active: Whether to activate the workflow (default: False)
        settings: Workflow settings (default: empty dict)
    
    Returns:
        String containing the created workflow ID and details
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    workflow_data = {
        "name": name,
        "nodes": nodes or [],
        "connections": connections or {},
        "active": active,
        "settings": settings or {}
    }
    
    try:
        response = await deps.http_client.post("/workflows", json=workflow_data)
        response.raise_for_status()
        result = response.json()
        workflow_id = result.get("id")
        
        logger.info(
            "workflow_created",
            extra={"workflow_id": workflow_id, "name": name, "active": active}
        )
        
        return f"Workflow created successfully. ID: {workflow_id}, Name: {name}, Active: {active}"
    
    except HTTPStatusError as e:
        error_msg = f"Failed to create workflow: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_creation_failed", extra={"error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error creating workflow: {str(e)}"
        logger.exception("workflow_creation_error")
        return error_msg


async def update_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    workflow_id: str,
    name: Optional[str] = None,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    active: Optional[bool] = None,
    settings: Optional[Dict[str, Any]] = None
) -> str:
    """
    Update an existing N8n workflow.
    
    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow ID to update
        name: New workflow name (optional)
        nodes: New workflow nodes (optional)
        connections: New workflow connections (optional)
        active: Whether to activate/deactivate (optional)
        settings: New workflow settings (optional)
    
    Returns:
        String containing the update result
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    # First, get the existing workflow
    try:
        get_response = await deps.http_client.get(f"/workflows/{workflow_id}")
        get_response.raise_for_status()
        existing_workflow = get_response.json()
    except HTTPStatusError as e:
        error_msg = f"Workflow not found: {workflow_id} - {e.response.status_code}"
        logger.error("workflow_not_found", extra={"workflow_id": workflow_id})
        return error_msg
    
    # Merge updates
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if nodes is not None:
        update_data["nodes"] = nodes
    if connections is not None:
        update_data["connections"] = connections
    if active is not None:
        update_data["active"] = active
    if settings is not None:
        update_data["settings"] = settings
    
    # Merge with existing workflow data
    updated_workflow = {**existing_workflow, **update_data}
    
    try:
        response = await deps.http_client.put(f"/workflows/{workflow_id}", json=updated_workflow)
        response.raise_for_status()
        result = response.json()
        
        logger.info("workflow_updated", extra={"workflow_id": workflow_id})
        
        changes = []
        if name is not None:
            changes.append(f"name: {name}")
        if nodes is not None:
            changes.append(f"nodes: {len(nodes)} nodes")
        if connections is not None:
            changes.append("connections updated")
        if active is not None:
            changes.append(f"active: {active}")
        if settings is not None:
            changes.append("settings updated")
        
        return f"Workflow {workflow_id} updated successfully. Changes: {', '.join(changes) if changes else 'none'}"
    
    except HTTPStatusError as e:
        error_msg = f"Failed to update workflow: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_update_failed", extra={"workflow_id": workflow_id, "error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error updating workflow: {str(e)}"
        logger.exception("workflow_update_error")
        return error_msg


async def delete_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    workflow_id: str
) -> str:
    """
    Delete an N8n workflow.
    
    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow ID to delete
    
    Returns:
        String containing the deletion result
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        response = await deps.http_client.delete(f"/workflows/{workflow_id}")
        response.raise_for_status()
        
        logger.info("workflow_deleted", extra={"workflow_id": workflow_id})
        
        return f"Workflow {workflow_id} deleted successfully"
    
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Workflow {workflow_id} not found"
        error_msg = f"Failed to delete workflow: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_deletion_failed", extra={"workflow_id": workflow_id, "error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error deleting workflow: {str(e)}"
        logger.exception("workflow_deletion_error")
        return error_msg


async def activate_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    workflow_id: str,
    active: bool
) -> str:
    """
    Activate or deactivate an N8n workflow.
    
    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow ID
        active: True to activate, False to deactivate
    
    Returns:
        String containing the activation result
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        # Get existing workflow
        get_response = await deps.http_client.get(f"/workflows/{workflow_id}")
        get_response.raise_for_status()
        workflow = get_response.json()
        
        # Update active status
        workflow["active"] = active
        
        # Update workflow
        response = await deps.http_client.put(f"/workflows/{workflow_id}", json=workflow)
        response.raise_for_status()
        
        status = "activated" if active else "deactivated"
        logger.info("workflow_activation_changed", extra={"workflow_id": workflow_id, "active": active})
        
        return f"Workflow {workflow_id} {status} successfully"
    
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Workflow {workflow_id} not found"
        error_msg = f"Failed to change workflow activation: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_activation_failed", extra={"workflow_id": workflow_id, "error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error changing workflow activation: {str(e)}"
        logger.exception("workflow_activation_error")
        return error_msg


async def list_workflows(
    ctx: RunContext[N8nWorkflowDeps],
    active_only: bool = False
) -> str:
    """
    List all N8n workflows.
    
    Args:
        ctx: Agent runtime context with dependencies
        active_only: If True, only return active workflows (default: False)
    
    Returns:
        String containing the list of workflows
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        response = await deps.http_client.get("/workflows")
        response.raise_for_status()
        workflows = response.json()
        
        if active_only:
            workflows = [w for w in workflows if w.get("active", False)]
        
        if not workflows:
            return "No workflows found" + (" (active only)" if active_only else "")
        
        result_parts = [f"Found {len(workflows)} workflow(s):\n"]
        for workflow in workflows:
            workflow_id = workflow.get("id", "unknown")
            name = workflow.get("name", "unnamed")
            active = workflow.get("active", False)
            status = "active" if active else "inactive"
            result_parts.append(f"- {name} (ID: {workflow_id}, Status: {status})")
        
        logger.info("workflows_listed", extra={"count": len(workflows), "active_only": active_only})
        
        return "\n".join(result_parts)
    
    except HTTPStatusError as e:
        error_msg = f"Failed to list workflows: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_list_failed", extra={"error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error listing workflows: {str(e)}"
        logger.exception("workflow_list_error")
        return error_msg


async def execute_workflow(
    ctx: RunContext[N8nWorkflowDeps],
    workflow_id: str,
    input_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Execute an N8n workflow.
    
    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow ID to execute
        input_data: Input data for workflow execution (default: empty dict)
    
    Returns:
        String containing the execution result
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    # N8n execution endpoint typically uses POST to /workflows/{id}/execute
    # or triggers via webhook. For manual execution, we use the execute endpoint.
    try:
        execution_data = input_data or {}
        
        # Try the execute endpoint (may vary by N8n version)
        response = await deps.http_client.post(
            f"/workflows/{workflow_id}/execute",
            json=execution_data
        )
        response.raise_for_status()
        result = response.json()
        
        execution_id = result.get("executionId") or result.get("id", "unknown")
        logger.info("workflow_executed", extra={"workflow_id": workflow_id, "execution_id": execution_id})
        
        return f"Workflow {workflow_id} executed successfully. Execution ID: {execution_id}"
    
    except HTTPStatusError as e:
        # If execute endpoint doesn't exist, try triggering via webhook
        if e.response.status_code == 404:
            # Get workflow to find webhook URL
            try:
                get_response = await deps.http_client.get(f"/workflows/{workflow_id}")
                get_response.raise_for_status()
                workflow = get_response.json()
                
                # Check if workflow has webhook trigger
                nodes = workflow.get("nodes", [])
                webhook_node = next((n for n in nodes if n.get("type") == "n8n-nodes-base.webhook"), None)
                
                if webhook_node:
                    webhook_path = webhook_node.get("parameters", {}).get("path", "")
                    return f"Workflow {workflow_id} uses webhook trigger. Use the webhook URL to execute it. Path: {webhook_path}"
                else:
                    return f"Workflow {workflow_id} does not support direct execution. It may require a trigger (webhook, schedule, etc.)"
            except Exception as inner_e:
                return f"Failed to check workflow execution method: {str(inner_e)}"
        
        error_msg = f"Failed to execute workflow: {e.response.status_code} - {e.response.text}"
        logger.error("workflow_execution_failed", extra={"workflow_id": workflow_id, "error": error_msg})
        return error_msg
    except Exception as e:
        error_msg = f"Error executing workflow: {str(e)}"
        logger.exception("workflow_execution_error")
        return error_msg


async def discover_n8n_nodes(
    ctx: RunContext[N8nWorkflowDeps],
    category: Optional[str] = None
) -> str:
    """
    Discover available N8n nodes via API.
    
    Args:
        ctx: Agent runtime context with dependencies
        category: Optional category filter (e.g., 'trigger', 'action', 'data')
    
    Returns:
        String containing available nodes with descriptions
    """
    deps = ctx.deps
    if not deps.http_client:
        await deps.initialize()
    
    try:
        # Try to get nodes from N8n API
        # Note: N8n API endpoint may vary by version
        # Common endpoints: /nodes, /node-types, /nodes/list
        
        # Try multiple possible endpoints
        endpoints_to_try = ["/nodes", "/node-types", "/nodes/list"]
        nodes_data = None
        
        for endpoint in endpoints_to_try:
            try:
                response = await deps.http_client.get(endpoint)
                if response.status_code == 200:
                    nodes_data = response.json()
                    break
            except:
                continue
        
        if not nodes_data:
            # Fallback: try to get from workflow execution context
            # Some N8n versions expose nodes via different endpoints
            return "Unable to discover nodes via API. N8n version may not support this endpoint. Use search_n8n_knowledge_base to find node information."
        
        # Process nodes data
        if isinstance(nodes_data, list):
            nodes = nodes_data
        elif isinstance(nodes_data, dict):
            nodes = nodes_data.get("data", nodes_data.get("nodes", []))
        else:
            nodes = []
        
        if not nodes:
            return "No nodes found in API response."
        
        # Filter by category if provided
        if category:
            category_lower = category.lower()
            nodes = [
                n for n in nodes
                if category_lower in str(n.get("category", "")).lower() or
                   category_lower in str(n.get("type", "")).lower()
            ]
        
        # Format response
        result_parts = [f"Found {len(nodes)} available N8n node(s):\n"]
        
        for node in nodes[:50]:  # Limit to 50 for readability
            node_name = node.get("name", node.get("displayName", "Unknown"))
            node_type = node.get("type", node.get("nodeType", "Unknown"))
            description = node.get("description", node.get("documentation", ""))
            category_info = node.get("category", "Unknown")
            
            result_parts.append(f"\n--- {node_name} ({node_type}) ---")
            result_parts.append(f"Category: {category_info}")
            if description:
                result_parts.append(f"Description: {description[:200]}...")
        
        if len(nodes) > 50:
            result_parts.append(f"\n... and {len(nodes) - 50} more nodes")
        
        logger.info("nodes_discovered", extra={"count": len(nodes), "category": category})
        
        return "\n".join(result_parts)
    
    except HTTPStatusError as e:
        error_msg = f"Failed to discover nodes: {e.response.status_code} - {e.response.text}"
        logger.error("node_discovery_failed", extra={"error": error_msg})
        return f"{error_msg}. Try using search_n8n_knowledge_base to find node information."
    except Exception as e:
        error_msg = f"Error discovering nodes: {str(e)}"
        logger.exception("node_discovery_error")
        return f"{error_msg}. Try using search_n8n_knowledge_base to find node information."


async def search_n8n_knowledge_base(
    ctx: RunContext[N8nWorkflowDeps],
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "hybrid"
) -> str:
    """
    Search the knowledge base for N8n-related information (nodes, workflows, examples).
    
    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text (e.g., "webhook node", "HTTP request workflow")
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic", "text", or "hybrid" (default: hybrid)
    
    Returns:
        String containing relevant information from the knowledge base
    """
    try:
        # Import RAG dependencies
        from server.projects.mongo_rag.dependencies import AgentDependencies
        from server.projects.mongo_rag.tools import semantic_search, hybrid_search, text_search
        
        # Initialize RAG dependencies
        agent_deps = AgentDependencies()
        await agent_deps.initialize()
        
        # Create a context wrapper for the search tools
        
        deps_ctx = DepsWrapper(agent_deps)
        
        # Perform the search based on type
        if search_type == "hybrid":
            results = await hybrid_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        elif search_type == "semantic":
            results = await semantic_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        else:
            results = await text_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        
        # Clean up
        await agent_deps.cleanup()
        
        # Format results as a simple string
        if not results:
            return f"No relevant information found in the knowledge base for: {query}"
        
        # Build a formatted response
        response_parts = [f"Found {len(results)} relevant document(s) about '{query}':\n"]
        
        for i, result in enumerate(results, 1):
            response_parts.append(f"\n--- Document {i}: {result.document_title} (relevance: {result.similarity:.2f}) ---")
            response_parts.append(f"Source: {result.document_source}")
            response_parts.append(f"Content: {result.content[:500]}...")  # Limit content length
        
        logger.info("n8n_knowledge_search_completed", extra={"query": query, "results": len(results)})
        
        return "\n".join(response_parts)
    
    except Exception as e:
        error_msg = f"Error searching knowledge base: {str(e)}"
        logger.exception("n8n_knowledge_search_error")
        return error_msg


async def search_node_examples(
    ctx: RunContext[N8nWorkflowDeps],
    node_type: Optional[str] = None,
    query: Optional[str] = None,
    match_count: Optional[int] = 5
) -> str:
    """
    Search for N8n node usage examples in the knowledge base.
    
    Args:
        ctx: Agent runtime context with dependencies
        node_type: Optional node type to filter by (e.g., "webhook", "HTTP Request")
        query: Optional search query for use cases or examples
        match_count: Number of results to return (default: 5)
    
    Returns:
        String containing node examples and usage patterns
    """
    try:
        # Import RAG dependencies
        from server.projects.mongo_rag.dependencies import AgentDependencies
        from server.projects.mongo_rag.tools import hybrid_search
        
        # Build search query
        if node_type and query:
            search_query = f"{node_type} node {query}"
        elif node_type:
            search_query = f"{node_type} node example configuration"
        elif query:
            search_query = f"n8n node {query} example"
        else:
            return "Please provide either node_type or query parameter"
        
        # Initialize RAG dependencies
        agent_deps = AgentDependencies()
        await agent_deps.initialize()
        
        # Create a context wrapper
        
        deps_ctx = DepsWrapper(agent_deps)
        
        # Perform hybrid search
        results = await hybrid_search(
            ctx=deps_ctx,
            query=search_query,
            match_count=match_count
        )
        
        # Clean up
        await agent_deps.cleanup()
        
        # Format results
        if not results:
            return f"No examples found for: {search_query}"
        
        response_parts = [f"Found {len(results)} example(s) for '{search_query}':\n"]
        
        for i, result in enumerate(results, 1):
            response_parts.append(f"\n--- Example {i}: {result.document_title} (relevance: {result.similarity:.2f}) ---")
            response_parts.append(f"Source: {result.document_source}")
            
            # Try to extract code/configuration blocks
            content = result.content
            if "```" in content or "{" in content:
                # Likely contains code/JSON configuration
                response_parts.append("Configuration/Code:")
                # Extract relevant portion
                if "```" in content:
                    code_start = content.find("```")
                    code_end = content.find("```", code_start + 3)
                    if code_end > code_start:
                        response_parts.append(content[code_start:code_end+3])
                    else:
                        response_parts.append(content[:800])
                else:
                    response_parts.append(content[:800])
            else:
                response_parts.append(content[:500])
        
        logger.info("node_examples_search_completed", extra={"query": search_query, "results": len(results)})
        
        return "\n".join(response_parts)
    
    except Exception as e:
        error_msg = f"Error searching node examples: {str(e)}"
        logger.exception("node_examples_search_error")
        return error_msg

