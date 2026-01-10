"""N8n Workflow project REST API."""

from fastapi import APIRouter, HTTPException
import logging

from server.core.api_utils import with_dependencies
from server.projects.n8n_workflow.models import (
    CreateWorkflowRequest,
    UpdateWorkflowRequest,
    DeleteWorkflowRequest,
    ActivateWorkflowRequest,
    ExecuteWorkflowRequest,
    WorkflowResponse,
    ListWorkflowsResponse,
    ExecuteWorkflowResponse
)
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
from server.projects.n8n_workflow.tools import (
    create_workflow,
    update_workflow,
    delete_workflow,
    activate_workflow,
    list_workflows,
    execute_workflow
)
from pydantic_ai.ag_ui import StateDeps
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=WorkflowResponse)
@with_dependencies(N8nWorkflowDeps)
async def create_workflow_endpoint(request: CreateWorkflowRequest, deps: N8nWorkflowDeps):
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
            settings=request.settings
        )
        
        # Extract workflow ID from result message if possible
        workflow_id = None
        if "ID: " in result:
            try:
                workflow_id = result.split("ID: ")[1].split(",")[0].strip()
            except:
                pass
        
        return WorkflowResponse(
            success="successfully" in result.lower() or "created" in result.lower(),
            workflow_id=workflow_id,
            message=result,
            data={"name": request.name, "active": request.active}
        )
    except Exception as e:
        logger.exception("workflow_creation_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update", response_model=WorkflowResponse)
@with_dependencies(N8nWorkflowDeps)
async def update_workflow_endpoint(request: UpdateWorkflowRequest, deps: N8nWorkflowDeps):
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
            settings=request.settings
        )
        
        return WorkflowResponse(
            success="successfully" in result.lower() or "updated" in result.lower(),
            workflow_id=request.workflow_id,
            message=result
        )
    except Exception as e:
        logger.exception("workflow_update_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=WorkflowResponse)
@with_dependencies(N8nWorkflowDeps)
async def delete_workflow_endpoint(request: DeleteWorkflowRequest, deps: N8nWorkflowDeps):
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
            message=result
        )
    except Exception as e:
        logger.exception("workflow_deletion_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate", response_model=WorkflowResponse)
@with_dependencies(N8nWorkflowDeps)
async def activate_workflow_endpoint(request: ActivateWorkflowRequest, deps: N8nWorkflowDeps):
    """
    Activate or deactivate an N8n workflow.
    """
    try:
        from pydantic_ai import RunContext
        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        
        result = await activate_workflow(
            run_ctx,
            workflow_id=request.workflow_id,
            active=request.active
        )
        
        return WorkflowResponse(
            success="successfully" in result.lower(),
            workflow_id=request.workflow_id,
            message=result,
            data={"active": request.active}
        )
    except Exception as e:
        logger.exception("workflow_activation_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ListWorkflowsResponse)
@with_dependencies(N8nWorkflowDeps)
async def list_workflows_endpoint(active_only: bool = False, deps: N8nWorkflowDeps = None):
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
            except:
                pass
        
        return ListWorkflowsResponse(
            success=True,
            workflows=workflows,
            count=len(workflows)
        )
    except Exception as e:
        logger.exception("workflow_list_error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteWorkflowResponse)
@with_dependencies(N8nWorkflowDeps)
async def execute_workflow_endpoint(request: ExecuteWorkflowRequest, deps: N8nWorkflowDeps):
    """
    Execute an N8n workflow.
    """
    try:
        from pydantic_ai import RunContext
        run_ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        
        result = await execute_workflow(
            run_ctx,
            workflow_id=request.workflow_id,
            input_data=request.input_data
        )
        
        # Extract execution ID if possible
        execution_id = None
        if "Execution ID: " in result:
            try:
                execution_id = result.split("Execution ID: ")[1].strip()
            except:
                pass
        
        return ExecuteWorkflowResponse(
            success="successfully" in result.lower() or "executed" in result.lower(),
            execution_id=execution_id,
            message=result
        )
    except Exception as e:
        logger.exception("workflow_execution_error")
        raise HTTPException(status_code=500, detail=str(e))

