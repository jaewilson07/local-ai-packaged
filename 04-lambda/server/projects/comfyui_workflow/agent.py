"""ComfyUI Workflow project agent for workflow management."""

import logging
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from server.projects.comfyui_workflow.dependencies import ComfyUIWorkflowDeps
from server.projects.comfyui_workflow.tools import (
    create_workflow_tool,
    delete_workflow_tool,
    get_workflow_tool,
    list_workflows_tool,
    update_workflow_tool,
)
from server.projects.shared.llm import get_llm_model

logger = logging.getLogger(__name__)


class ComfyUIWorkflowState(BaseModel):
    """Minimal shared state for the ComfyUI Workflow agent."""


COMFYUI_WORKFLOW_SYSTEM_PROMPT = """You are a ComfyUI workflow management agent that helps users manage and execute ComfyUI workflows.

You can:
- Create new ComfyUI workflows
- List and retrieve workflows
- Update existing workflows
- Delete workflows
- Run workflows with parameters
- Manage LoRA models and character-based workflows

All operations are scoped to the authenticated user's workflows for data isolation.
"""


comfyui_workflow_agent = Agent(
    model=get_llm_model(),
    system_prompt=COMFYUI_WORKFLOW_SYSTEM_PROMPT,
    deps_type=ComfyUIWorkflowDeps,
    state_type=ComfyUIWorkflowState,
)


@comfyui_workflow_agent.tool
async def create_workflow(
    ctx: RunContext[ComfyUIWorkflowDeps],
    user_id: str = Field(..., description="User UUID"),
    name: str = Field(..., description="Workflow name"),
    workflow_json: dict = Field(..., description="ComfyUI workflow JSON"),
    description: str | None = Field(None, description="Workflow description"),
    is_public: bool = Field(False, description="Whether workflow is public"),
    tags: list[str] | None = Field(None, description="Workflow tags"),
    parameter_schema: dict | None = Field(None, description="Parameter schema"),
) -> dict:
    """
    Create a new ComfyUI workflow.

    Args:
        user_id: User UUID as string
        name: Workflow name
        workflow_json: ComfyUI workflow JSON
        description: Optional workflow description
        is_public: Whether workflow is public
        tags: Optional workflow tags
        parameter_schema: Optional parameter schema

    Returns:
        Created workflow response
    """
    try:
        user_uuid = UUID(user_id)

        result = await create_workflow_tool(
            ctx=ctx,
            user_id=user_uuid,
            name=name,
            workflow_json=workflow_json,
            description=description,
            is_public=is_public,
            tags=tags,
            parameter_schema=parameter_schema,
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: create_workflow")
        raise RuntimeError(f"Failed to create workflow: {e}")


@comfyui_workflow_agent.tool
async def list_workflows(
    ctx: RunContext[ComfyUIWorkflowDeps],
    user_id: str = Field(..., description="User UUID"),
    is_public: bool | None = Field(None, description="Filter by public status"),
    limit: int = Field(100, description="Maximum number of workflows"),
    offset: int = Field(0, description="Offset for pagination"),
) -> dict:
    """
    List workflows for a user.

    Args:
        user_id: User UUID as string
        is_public: Filter by public status
        limit: Maximum number of workflows
        offset: Offset for pagination

    Returns:
        List of workflows
    """
    try:
        user_uuid = UUID(user_id)

        result = await list_workflows_tool(
            ctx=ctx,
            user_id=user_uuid,
            is_public=is_public,
            limit=limit,
            offset=offset,
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: list_workflows")
        raise RuntimeError(f"Failed to list workflows: {e}")


@comfyui_workflow_agent.tool
async def get_workflow(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: str = Field(..., description="Workflow UUID"),
    user_id: str = Field(..., description="User UUID"),
) -> dict:
    """
    Get a workflow by ID.

    Args:
        workflow_id: Workflow UUID as string
        user_id: User UUID as string

    Returns:
        Workflow response
    """
    try:
        workflow_uuid = UUID(workflow_id)
        user_uuid = UUID(user_id)

        result = await get_workflow_tool(
            ctx=ctx,
            workflow_id=workflow_uuid,
            user_id=user_uuid,
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: get_workflow")
        raise RuntimeError(f"Failed to get workflow: {e}")


@comfyui_workflow_agent.tool
async def update_workflow(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: str = Field(..., description="Workflow UUID"),
    user_id: str = Field(..., description="User UUID"),
    name: str | None = Field(None, description="New name"),
    description: str | None = Field(None, description="New description"),
    workflow_json: dict | None = Field(None, description="New workflow JSON"),
    is_public: bool | None = Field(None, description="New public status"),
    tags: list[str] | None = Field(None, description="New tags"),
    parameter_schema: dict | None = Field(None, description="New parameter schema"),
    status: str | None = Field(None, description="New status"),
) -> dict:
    """
    Update a workflow.

    Args:
        workflow_id: Workflow UUID as string
        user_id: User UUID as string
        name: Optional new name
        description: Optional new description
        workflow_json: Optional new workflow JSON
        is_public: Optional new public status
        tags: Optional new tags
        parameter_schema: Optional new parameter schema
        status: Optional new status

    Returns:
        Updated workflow response
    """
    try:
        workflow_uuid = UUID(workflow_id)
        user_uuid = UUID(user_id)

        result = await update_workflow_tool(
            ctx=ctx,
            workflow_id=workflow_uuid,
            user_id=user_uuid,
            name=name,
            description=description,
            workflow_json=workflow_json,
            is_public=is_public,
            tags=tags,
            parameter_schema=parameter_schema,
            status=status,
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: update_workflow")
        raise RuntimeError(f"Failed to update workflow: {e}")


@comfyui_workflow_agent.tool
async def delete_workflow(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: str = Field(..., description="Workflow UUID"),
    user_id: str = Field(..., description="User UUID"),
) -> dict:
    """
    Delete a workflow.

    Args:
        workflow_id: Workflow UUID as string
        user_id: User UUID as string

    Returns:
        Success status
    """
    try:
        workflow_uuid = UUID(workflow_id)
        user_uuid = UUID(user_id)

        result = await delete_workflow_tool(
            ctx=ctx,
            workflow_id=workflow_uuid,
            user_id=user_uuid,
        )

        return result
    except Exception as e:
        logger.exception("agent_tool_error: delete_workflow")
        raise RuntimeError(f"Failed to delete workflow: {e}")
