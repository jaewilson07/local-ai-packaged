"""FastAPI router for ComfyUI workflow management."""

import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from uuid import UUID

from server.projects.auth.dependencies import get_current_user, User
from server.projects.comfyui_workflow.dependencies import (
    ComfyUIWorkflowDeps,
    get_comfyui_workflow_deps
)
from server.projects.comfyui_workflow.stores.supabase_store import SupabaseWorkflowStore
from server.projects.comfyui_workflow.services.comfyui_service import ComfyUIService
from server.projects.comfyui_workflow.services.lora_sync_service import LoRASyncService
from server.projects.comfyui_workflow.models import (
    CreateWorkflowRequest,
    UpdateWorkflowRequest,
    WorkflowResponse,
    ListWorkflowsResponse,
    RunWorkflowRequest,
    WorkflowRunResponse,
    ListWorkflowRunsResponse,
    CreateLoRAModelRequest,
    ImportLoRAFromGoogleDriveRequest,
    LoRAModelResponse,
    ListLoRAModelsResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Workflow CRUD endpoints

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Create a new ComfyUI workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        workflow = await store.create_workflow(
            user_id=user_id,
            name=request.name,
            workflow_json=request.workflow_json,
            description=request.description,
            is_public=request.is_public,
            tags=request.tags
        )
        return workflow
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.get("/workflows", response_model=ListWorkflowsResponse)
async def list_workflows(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    is_public: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user)
):
    """List workflows for the authenticated user."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        workflows = await store.list_workflows(
            user_id=user_id,
            is_public=is_public,
            limit=limit,
            offset=offset
        )
        return ListWorkflowsResponse(workflows=workflows, count=len(workflows))
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Get a workflow by ID."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        workflow = await store.get_workflow(workflow_id, user_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    request: UpdateWorkflowRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Update a workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        workflow = await store.update_workflow(
            workflow_id=workflow_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            workflow_json=request.workflow_json,
            is_public=request.is_public,
            tags=request.tags
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or not owned by user")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Delete a workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        deleted = await store.delete_workflow(workflow_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workflow not found or not owned by user")
        return {"success": True, "message": "Workflow deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow: {str(e)}")


# Workflow execution endpoints

@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    request: Optional[RunWorkflowRequest] = None,
    user: User = Depends(get_current_user)
):
    """Execute a workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    # Get workflow
    workflow = await store.get_workflow(workflow_id, user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Initialize services
    lora_sync_service = LoRASyncService(
        minio_service=deps.minio_service,
        google_drive_service=deps.google_drive_service
    )
    comfyui_service = ComfyUIService(
        http_client=deps.comfyui_http_client,
        base_url=deps.comfyui_url,
        lora_sync_service=lora_sync_service
    )
    
    # Prepare workflow JSON (merge input params if provided)
    workflow_json = workflow.workflow_json.copy()
    if request and request.input_params:
        # Merge input_params into workflow (override node inputs)
        for node_id, node_data in workflow_json.items():
            if isinstance(node_data, dict) and "inputs" in node_data:
                node_inputs = node_data["inputs"]
                # Check if any input_params match this node's inputs
                for key, value in request.input_params.items():
                    if key in node_inputs:
                        node_inputs[key] = value
    
    try:
        # Submit workflow to ComfyUI
        comfyui_request_id = await comfyui_service.submit_workflow(
            workflow_json=workflow_json,
            user_id=user_id
        )
        
        if not comfyui_request_id:
            raise HTTPException(status_code=500, detail="Failed to submit workflow to ComfyUI")
        
        # Create workflow run record
        workflow_run = await store.create_workflow_run(
            workflow_id=workflow_id,
            user_id=user_id,
            comfyui_request_id=comfyui_request_id,
            input_params=request.input_params if request else None
        )
        
        return workflow_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run workflow: {str(e)}")


@router.get("/workflows/{workflow_id}/runs", response_model=ListWorkflowRunsResponse)
async def list_workflow_runs(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user)
):
    """List workflow runs for a workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        runs = await store.list_workflow_runs(
            user_id=user_id,
            workflow_id=workflow_id,
            limit=limit,
            offset=offset
        )
        return ListWorkflowRunsResponse(runs=runs, count=len(runs))
    except Exception as e:
        logger.error(f"Failed to list workflow runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflow runs: {str(e)}")


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Get workflow run status and result."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        run = await store.get_workflow_run(run_id, user_id)
        if not run:
            raise HTTPException(status_code=404, detail="Workflow run not found")
        
        # If run is still pending/running, check ComfyUI for updates
        if run.status in ("pending", "running") and run.comfyui_request_id:
            lora_sync_service = LoRASyncService(
                minio_service=deps.minio_service,
                google_drive_service=deps.google_drive_service
            )
            comfyui_service = ComfyUIService(
                http_client=deps.comfyui_http_client,
                base_url=deps.comfyui_url,
                lora_sync_service=lora_sync_service
            )
            
            status = await comfyui_service.get_job_status(run.comfyui_request_id)
            if status:
                # Update run status
                new_status = status.get("status", run.status)
                output_images = status.get("output_images", [])
                error_message = status.get("error")
                
                updated_run = await store.update_workflow_run(
                    run_id=run_id,
                    user_id=user_id,
                    status=new_status,
                    output_images=output_images,
                    error_message=error_message
                )
                
                if updated_run:
                    return updated_run
        
        return run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow run: {str(e)}")


# LoRA model endpoints

@router.post("/loras", response_model=LoRAModelResponse)
async def create_lora_model(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    file: UploadFile = File(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list] = None,
    user: User = Depends(get_current_user)
):
    """Upload a LoRA model and create metadata."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Read file
    file_data = await file.read()
    file_size = len(file_data)
    filename = file.filename or "unnamed.safetensors"
    
    # Upload to MinIO
    try:
        minio_path = await deps.minio_service.upload_file(
            user_id=user_id,
            file_data=file_data,
            object_key=f"loras/{filename}",
            content_type=file.content_type
        )
    except Exception as e:
        logger.error(f"Failed to upload LoRA to MinIO: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload LoRA: {str(e)}")
    
    # Create metadata in Supabase
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        lora_model = await store.create_lora_model(
            user_id=user_id,
            name=name or filename,
            filename=filename,
            minio_path=minio_path,
            file_size=file_size,
            description=description,
            tags=tags or []
        )
        return lora_model
    except Exception as e:
        logger.error(f"Failed to create LoRA metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create LoRA metadata: {str(e)}")


@router.post("/loras/import-from-google-drive", response_model=LoRAModelResponse)
async def import_lora_from_google_drive(
    request: ImportLoRAFromGoogleDriveRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Import a LoRA model from Google Drive."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if not deps.google_drive_service:
        raise HTTPException(status_code=503, detail="Google Drive service not available")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    lora_sync_service = LoRASyncService(
        minio_service=deps.minio_service,
        google_drive_service=deps.google_drive_service
    )
    
    try:
        # Get file metadata from Google Drive
        file_metadata = deps.google_drive_service.api.get_file_metadata(
            request.google_drive_file_id,
            fields="id,name,size"
        )
        
        filename = request.name or file_metadata.get("name", "lora.safetensors")
        file_size = file_metadata.get("size")
        
        # Download from Google Drive
        logger.info(f"Downloading LoRA from Google Drive: {request.google_drive_file_id} for user {user_id}")
        file_data = deps.google_drive_service.download_file(request.google_drive_file_id)
        
        # Upload to MinIO
        minio_path = await deps.minio_service.upload_file(
            user_id=user_id,
            file_data=file_data,
            object_key=f"loras/{filename}",
            content_type="application/octet-stream"
        )
        
        # Create metadata in Supabase
        lora_model = await store.create_lora_model(
            user_id=user_id,
            name=request.name or filename,
            filename=filename,
            minio_path=minio_path,
            file_size=file_size or len(file_data),
            description=request.description,
            tags=request.tags or []
        )
        
        logger.info(f"Imported LoRA from Google Drive: {filename} for user {user_id}")
        return lora_model
        
    except ValueError as e:
        logger.error(f"Failed to import LoRA from Google Drive: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import LoRA: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to import LoRA from Google Drive: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import LoRA: {str(e)}")


@router.get("/loras", response_model=ListLoRAModelsResponse)
async def list_lora_models(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user)
):
    """List LoRA models for the authenticated user."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        models = await store.list_lora_models(user_id=user_id, limit=limit, offset=offset)
        return ListLoRAModelsResponse(models=models, count=len(models))
    except Exception as e:
        logger.error(f"Failed to list LoRA models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list LoRA models: {str(e)}")


@router.get("/loras/{lora_id}", response_model=LoRAModelResponse)
async def get_lora_model(
    lora_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Get LoRA model metadata."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    try:
        model = await store.get_lora_model(lora_id, user_id)
        if not model:
            raise HTTPException(status_code=404, detail="LoRA model not found")
        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get LoRA model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get LoRA model: {str(e)}")


@router.delete("/loras/{lora_id}")
async def delete_lora_model(
    lora_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user)
):
    """Delete a LoRA model (both metadata and file)."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    store = SupabaseWorkflowStore(deps.supabase_service)
    
    # Get model to find filename
    model = await store.get_lora_model(lora_id, user_id)
    if not model:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    
    try:
        # Delete from MinIO
        await deps.minio_service.delete_file(user_id=user_id, object_key=f"loras/{model.filename}")
        
        # Delete metadata
        deleted = await store.delete_lora_model(lora_id, user_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete LoRA metadata")
        
        return {"success": True, "message": "LoRA model deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete LoRA model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete LoRA model: {str(e)}")
