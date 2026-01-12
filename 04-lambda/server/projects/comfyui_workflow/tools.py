"""Core capability tools for ComfyUI Workflow project."""

import logging
from uuid import UUID

from pydantic_ai import RunContext

from server.projects.comfyui_workflow.dependencies import ComfyUIWorkflowDeps
from server.projects.comfyui_workflow.models import (
    ListWorkflowsResponse,
    WorkflowResponse,
)
from server.projects.comfyui_workflow.stores.supabase_store import SupabaseWorkflowStore

logger = logging.getLogger(__name__)


async def create_workflow_tool(
    ctx: RunContext[ComfyUIWorkflowDeps],
    user_id: UUID,
    name: str,
    workflow_json: dict,
    description: str | None = None,
    is_public: bool = False,
    tags: list[str] | None = None,
    parameter_schema: dict | None = None,
) -> WorkflowResponse:
    """
    Create a new ComfyUI workflow.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        name: Workflow name
        workflow_json: ComfyUI workflow JSON
        description: Optional workflow description
        is_public: Whether workflow is public
        tags: Optional workflow tags
        parameter_schema: Optional parameter schema

    Returns:
        Created workflow response
    """
    deps = ctx.deps
    if not deps.supabase_service:
        await deps.initialize()

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflow = await store.create_workflow(
            user_id=user_id,
            name=name,
            workflow_json=workflow_json,
            description=description,
            is_public=is_public,
            tags=tags or [],
            parameter_schema=parameter_schema,
        )

        logger.info(
            "workflow_created",
            extra={"user_id": str(user_id), "workflow_id": str(workflow.id), "name": name},
        )

        return workflow
    except Exception as e:
        logger.exception(
            "workflow_creation_failed", extra={"user_id": str(user_id), "error": str(e)}
        )
        raise


async def list_workflows_tool(
    ctx: RunContext[ComfyUIWorkflowDeps],
    user_id: UUID,
    is_public: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ListWorkflowsResponse:
    """
    List workflows for a user.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        is_public: Filter by public status
        limit: Maximum number of workflows to return
        offset: Offset for pagination

    Returns:
        List of workflows
    """
    deps = ctx.deps
    if not deps.supabase_service:
        await deps.initialize()

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflows = await store.list_workflows(
            user_id=user_id,
            is_public=is_public,
            limit=limit,
            offset=offset,
        )

        logger.info("workflows_listed", extra={"user_id": str(user_id), "count": len(workflows)})

        return ListWorkflowsResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        logger.exception("workflow_list_failed", extra={"user_id": str(user_id), "error": str(e)})
        raise


async def get_workflow_tool(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: UUID,
    user_id: UUID,
) -> WorkflowResponse:
    """
    Get a workflow by ID.

    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow UUID
        user_id: User UUID

    Returns:
        Workflow response
    """
    deps = ctx.deps
    if not deps.supabase_service:
        await deps.initialize()

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflow = await store.get_workflow(workflow_id, user_id)

        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        logger.info(
            "workflow_retrieved", extra={"user_id": str(user_id), "workflow_id": str(workflow_id)}
        )

        return workflow
    except Exception as e:
        logger.exception(
            "workflow_retrieval_failed", extra={"workflow_id": str(workflow_id), "error": str(e)}
        )
        raise


async def update_workflow_tool(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: UUID,
    user_id: UUID,
    name: str | None = None,
    description: str | None = None,
    workflow_json: dict | None = None,
    is_public: bool | None = None,
    tags: list[str] | None = None,
    parameter_schema: dict | None = None,
    status: str | None = None,
) -> WorkflowResponse:
    """
    Update a workflow.

    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow UUID
        user_id: User UUID
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
    deps = ctx.deps
    if not deps.supabase_service:
        await deps.initialize()

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflow = await store.update_workflow(
            workflow_id=workflow_id,
            user_id=user_id,
            name=name,
            description=description,
            workflow_json=workflow_json,
            is_public=is_public,
            tags=tags,
            parameter_schema=parameter_schema,
            status=status,
        )

        if not workflow:
            raise ValueError(f"Workflow not found or not owned by user: {workflow_id}")

        logger.info(
            "workflow_updated", extra={"user_id": str(user_id), "workflow_id": str(workflow_id)}
        )

        return workflow
    except Exception as e:
        logger.exception(
            "workflow_update_failed", extra={"workflow_id": str(workflow_id), "error": str(e)}
        )
        raise


async def delete_workflow_tool(
    ctx: RunContext[ComfyUIWorkflowDeps],
    workflow_id: UUID,
    user_id: UUID,
) -> dict:
    """
    Delete a workflow.

    Args:
        ctx: Agent runtime context with dependencies
        workflow_id: Workflow UUID
        user_id: User UUID

    Returns:
        Success status
    """
    deps = ctx.deps
    if not deps.supabase_service:
        await deps.initialize()

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        deleted = await store.delete_workflow(workflow_id, user_id)

        if not deleted:
            raise ValueError(f"Workflow not found or not owned by user: {workflow_id}")

        logger.info(
            "workflow_deleted", extra={"user_id": str(user_id), "workflow_id": str(workflow_id)}
        )

        return {"success": True, "message": "Workflow deleted"}
    except Exception as e:
        logger.exception(
            "workflow_delete_failed", extra={"workflow_id": str(workflow_id), "error": str(e)}
        )
        raise
