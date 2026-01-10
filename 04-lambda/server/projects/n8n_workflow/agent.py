"""Main N8n Workflow agent implementation."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pydantic_ai.ag_ui import StateDeps

from server.projects.shared.llm import get_llm_model as _get_n8n_workflow_model
from server.projects.shared.wrappers import DepsWrapper
from server.projects.n8n_workflow.config import config
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
from server.projects.n8n_workflow.prompts import N8N_WORKFLOW_SYSTEM_PROMPT
from server.projects.n8n_workflow.tools import (
    create_workflow,
    update_workflow,
    delete_workflow,
    activate_workflow,
    list_workflows,
    execute_workflow,
    discover_n8n_nodes,
    search_n8n_knowledge_base,
    search_node_examples
)


class N8nWorkflowState(BaseModel):
    """Minimal shared state for the N8n workflow agent."""
    pass


# Create the N8n workflow agent with AGUI support
n8n_workflow_agent = Agent(
    _get_n8n_workflow_model(),
    deps_type=StateDeps[N8nWorkflowState],
    system_prompt=N8N_WORKFLOW_SYSTEM_PROMPT
)


# Register tools - create wrapper functions that bridge StateDeps to N8nWorkflowDeps
@n8n_workflow_agent.tool
async def create_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    name: str,
    nodes: Optional[List[Dict[str, Any]]] = None,
    connections: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    active: bool = False,
    settings: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new N8n workflow.
    
    Args:
        ctx: Agent runtime context with state dependencies
        name: Workflow name
        nodes: List of workflow nodes (optional)
        connections: Workflow connections (optional)
        active: Whether to activate the workflow (default: False)
        settings: Workflow settings (optional)
    
    Returns:
        String containing the created workflow ID and details
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await create_workflow(deps_ctx, name, nodes, connections, active, settings)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def update_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
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
        ctx: Agent runtime context with state dependencies
        workflow_id: Workflow ID to update
        name: New workflow name (optional)
        nodes: New workflow nodes (optional)
        connections: New workflow connections (optional)
        active: Whether to activate/deactivate (optional)
        settings: New workflow settings (optional)
    
    Returns:
        String containing the update result
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await update_workflow(deps_ctx, workflow_id, name, nodes, connections, active, settings)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def delete_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    workflow_id: str
) -> str:
    """
    Delete an N8n workflow.
    
    Args:
        ctx: Agent runtime context with state dependencies
        workflow_id: Workflow ID to delete
    
    Returns:
        String containing the deletion result
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await delete_workflow(deps_ctx, workflow_id)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def activate_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    workflow_id: str,
    active: bool
) -> str:
    """
    Activate or deactivate an N8n workflow.
    
    Args:
        ctx: Agent runtime context with state dependencies
        workflow_id: Workflow ID
        active: True to activate, False to deactivate
    
    Returns:
        String containing the activation result
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await activate_workflow(deps_ctx, workflow_id, active)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def list_workflows_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    active_only: bool = False
) -> str:
    """
    List all N8n workflows.
    
    Args:
        ctx: Agent runtime context with state dependencies
        active_only: If True, only return active workflows (default: False)
    
    Returns:
        String containing the list of workflows
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await list_workflows(deps_ctx, active_only)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def execute_workflow_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    workflow_id: str,
    input_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Execute an N8n workflow.
    
    Args:
        ctx: Agent runtime context with state dependencies
        workflow_id: Workflow ID to execute
        input_data: Input data for workflow execution (optional)
    
    Returns:
        String containing the execution result
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await execute_workflow(deps_ctx, workflow_id, input_data)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def discover_n8n_nodes_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    category: Optional[str] = None
) -> str:
    """
    Discover available N8n nodes via API.
    
    Args:
        ctx: Agent runtime context with state dependencies
        category: Optional category filter (e.g., 'trigger', 'action', 'data')
    
    Returns:
        String containing available nodes with descriptions
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await discover_n8n_nodes(deps_ctx, category)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def search_n8n_knowledge_base_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "hybrid"
) -> str:
    """
    Search the knowledge base for N8n-related information (nodes, workflows, examples).
    
    ALWAYS use this before creating workflows to find relevant information.
    
    Args:
        ctx: Agent runtime context with state dependencies
        query: Search query text (e.g., "webhook node", "HTTP request workflow")
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic", "text", or "hybrid" (default: hybrid)
    
    Returns:
        String containing relevant information from the knowledge base
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await search_n8n_knowledge_base(deps_ctx, query, match_count, search_type)
    finally:
        await deps.cleanup()


@n8n_workflow_agent.tool
async def search_node_examples_tool(
    ctx: RunContext[StateDeps[N8nWorkflowState]],
    node_type: Optional[str] = None,
    query: Optional[str] = None,
    match_count: Optional[int] = 5
) -> str:
    """
    Search for N8n node usage examples in the knowledge base.
    
    Args:
        ctx: Agent runtime context with state dependencies
        node_type: Optional node type to filter by (e.g., "webhook", "HTTP Request")
        query: Optional search query for use cases or examples
        match_count: Number of results to return (default: 5)
    
    Returns:
        String containing node examples and usage patterns
    """
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    
    deps_ctx = DepsWrapper(deps)
    try:
        return await search_node_examples(deps_ctx, node_type, query, match_count)
    finally:
        await deps.cleanup()

