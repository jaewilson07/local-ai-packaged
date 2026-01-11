"""N8n Workflow project REST API."""

import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
from server.projects.n8n_workflow.models import (
    ActivateWorkflowRequest,
    CreateWorkflowRequest,
    DeleteWorkflowRequest,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ListWorkflowsResponse,
    UpdateWorkflowRequest,
    WorkflowResponse,
)
from server.projects.n8n_workflow.tools import (
    activate_workflow,
    create_workflow,
    delete_workflow,
    execute_workflow,
    list_workflows,
    update_workflow,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# FastAPI dependency function with yield pattern for resource cleanup
async def get_n8n_workflow_deps() -> AsyncGenerator[N8nWorkflowDeps, None]:
    """FastAPI dependency that yields N8nWorkflowDeps."""
    deps = N8nWorkflowDeps.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()


@router.post("/create", response_model=WorkflowResponse)
async def create_workflow_endpoint(
    request: CreateWorkflowRequest, deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)]
):
    """
    Create a new N8n workflow.

    Creates a workflow with the specified nodes, connections, and settings.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        # Convert request to dict for tool
        nodes_dict = [node.dict() for node in request.nodes] if request.nodes else []

        result = await create_workflow(
            run_ctx,
            name=request.name,
            nodes=nodes_dict,
            connections=request.connections,
            active=request.active,
            settings=request.settings,
        )

        # Extract workflow ID from result message if possible
        workflow_id = None
        if "ID: " in result:
            with contextlib.suppress(BaseException):
                workflow_id = result.split("ID: ")[1].split(",")[0].strip()

        return WorkflowResponse(
            success="successfully" in result.lower() or "created" in result.lower(),
            workflow_id=workflow_id,
            message=result,
            data={"name": request.name, "active": request.active},
        )
    except Exception as e:
        logger.exception("workflow_creation_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=WorkflowResponse)
async def update_workflow_endpoint(
    request: UpdateWorkflowRequest, deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)]
):
    """
    Update an existing N8n workflow.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        nodes_dict = [node.dict() for node in request.nodes] if request.nodes else None

        result = await update_workflow(
            run_ctx,
            workflow_id=request.workflow_id,
            name=request.name,
            nodes=nodes_dict,
            connections=request.connections,
            active=request.active,
            settings=request.settings,
        )

        return WorkflowResponse(
            success="successfully" in result.lower() or "updated" in result.lower(),
            workflow_id=request.workflow_id,
            message=result,
        )
    except Exception as e:
        logger.exception("workflow_update_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=WorkflowResponse)
async def delete_workflow_endpoint(
    request: DeleteWorkflowRequest, deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)]
):
    """
    Delete an N8n workflow.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        result = await delete_workflow(run_ctx, workflow_id=request.workflow_id)

        return WorkflowResponse(
            success="successfully" in result.lower() or "deleted" in result.lower(),
            workflow_id=request.workflow_id,
            message=result,
        )
    except Exception as e:
        logger.exception("workflow_deletion_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate", response_model=WorkflowResponse)
async def activate_workflow_endpoint(
    request: ActivateWorkflowRequest,
    deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)],
):
    """
    Activate or deactivate an N8n workflow.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        result = await activate_workflow(
            run_ctx, workflow_id=request.workflow_id, active=request.active
        )

        return WorkflowResponse(
            success="successfully" in result.lower(),
            workflow_id=request.workflow_id,
            message=result,
            data={"active": request.active},
        )
    except Exception as e:
        logger.exception("workflow_activation_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ListWorkflowsResponse)
async def list_workflows_endpoint(
    deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)], active_only: bool = False
):
    """
    List all N8n workflows.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        result = await list_workflows(run_ctx, active_only=active_only)

        # Parse result to extract workflow list
        workflows = []
        if "Found" in result and "workflow" in result:
            # Try to get actual workflows from API
            try:
                response = await deps.http_client.get("/workflows")
                response.raise_for_status()
                workflows = response.json()
                if active_only:
                    workflows = [w for w in workflows if w.get("active", False)]
            except Exception:
                pass

        return ListWorkflowsResponse(success=True, workflows=workflows, count=len(workflows))
    except Exception as e:
        logger.exception("workflow_list_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow_endpoint(
    request: ExecuteWorkflowRequest,
    deps: Annotated[N8nWorkflowDeps, Depends(get_n8n_workflow_deps)],
):
    """
    Execute an N8n workflow.
    """
    try:
        from pydantic_ai import RunContext

        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")

        result = await execute_workflow(
            run_ctx, workflow_id=request.workflow_id, input_data=request.input_data
        )

        # Extract execution ID if possible
        execution_id = None
        if "Execution ID: " in result:
            with contextlib.suppress(BaseException):
                execution_id = result.split("Execution ID: ")[1].strip()

        return ExecuteWorkflowResponse(
            success="successfully" in result.lower() or "executed" in result.lower(),
            execution_id=execution_id,
            message=result,
        )
    except Exception as e:
        logger.exception("workflow_execution_error")
        raise HTTPException(status_code=500, detail=str(e))
