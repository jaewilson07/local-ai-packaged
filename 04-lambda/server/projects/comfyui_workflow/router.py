"""FastAPI router for ComfyUI workflow management."""

import logging
import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from server.projects.auth.dependencies import User, get_current_user
from server.projects.comfyui_workflow.dependencies import (
    ComfyUIWorkflowDeps,
    get_comfyui_workflow_deps,
)
from server.projects.comfyui_workflow.models import (
    CreateWorkflowRequest,
    GenerateWorkflowRequest,
    ImportLoRAFromGoogleDriveRequest,
    ListLoRAModelsResponse,
    ListWorkflowRunsResponse,
    ListWorkflowsResponse,
    LoRAModelResponse,
    RunWorkflowRequest,
    UpdateWorkflowRequest,
    WorkflowResponse,
    WorkflowRunResponse,
)
from server.projects.comfyui_workflow.services.comfyui_service import ComfyUIService
from server.projects.comfyui_workflow.services.immich_service import ImmichService
from server.projects.comfyui_workflow.services.lora_resolution_service import LoRAResolutionService
from server.projects.comfyui_workflow.services.lora_sync_service import LoRASyncService
from server.projects.comfyui_workflow.services.parameter_service import (
    ParameterService,
    ParameterValidationError,
)
from server.projects.comfyui_workflow.stores.supabase_store import SupabaseWorkflowStore

router = APIRouter()
logger = logging.getLogger(__name__)


# Workflow CRUD endpoints


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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
            tags=request.tags,
            parameter_schema=request.parameter_schema,
        )
        return workflow
    except HTTPException:
        raise


@router.get("/workflows", response_model=ListWorkflowsResponse)
async def list_workflows(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    is_public: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """List workflows for the authenticated user."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflows = await store.list_workflows(
            user_id=user_id, is_public=is_public, limit=limit, offset=offset
        )
        return ListWorkflowsResponse(workflows=workflows, count=len(workflows))
    except HTTPException:
        raise


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    request: UpdateWorkflowRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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
            tags=request.tags,
            parameter_schema=request.parameter_schema,
            status=request.status,
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or not owned by user")
        return workflow
    except HTTPException:
        raise


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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


# Workflow publishing endpoints


@router.get("/workflows/published", response_model=ListWorkflowsResponse)
async def list_published_workflows(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    tags: list | None = None,
    user: User = Depends(get_current_user),
):
    """List all published workflows (available to all users)."""
    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflows = await store.list_published_workflows(limit=limit, offset=offset, tags=tags)
        return ListWorkflowsResponse(workflows=workflows, count=len(workflows))
    except HTTPException:
        raise


@router.put("/workflows/{workflow_id}/publish", response_model=WorkflowResponse)
async def publish_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
):
    """Publish a workflow (make it available to all users)."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflow = await store.publish_workflow(workflow_id, user_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or not owned by user")
        return workflow
    except HTTPException:
        raise


@router.put("/workflows/{workflow_id}/unpublish", response_model=WorkflowResponse)
async def unpublish_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
):
    """Unpublish a workflow (set status back to draft)."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        workflow = await store.unpublish_workflow(workflow_id, user_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or not owned by user")
        return workflow
    except HTTPException:
        raise


# Workflow execution endpoints


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    request: RunWorkflowRequest | None = None,
    user: User = Depends(get_current_user),
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
        minio_service=deps.minio_service, google_drive_service=deps.google_drive_service
    )
    comfyui_service = ComfyUIService(
        http_client=deps.comfyui_http_client,
        base_url=deps.comfyui_url,
        lora_sync_service=lora_sync_service,
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
            workflow_json=workflow_json, user_id=user_id
        )

        if not comfyui_request_id:
            raise HTTPException(status_code=500, detail="Failed to submit workflow to ComfyUI")

        # Create workflow run record
        workflow_run = await store.create_workflow_run(
            workflow_id=workflow_id,
            user_id=user_id,
            comfyui_request_id=comfyui_request_id,
            input_params=request.input_params if request else None,
        )

        return workflow_run

    except HTTPException:
        raise


@router.post("/workflows/{workflow_id}/generate", response_model=WorkflowRunResponse)
async def generate_workflow(
    workflow_id: UUID,
    request: GenerateWorkflowRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
):
    """Generate images with parameterized workflow execution."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    # Get workflow (must be published or owned by user)
    workflow = await store.get_workflow(workflow_id, user_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if workflow is published (or user owns it)
    if workflow.status != "published" and workflow.user_id != user_id:
        raise HTTPException(status_code=403, detail="Workflow is not published")

    # Initialize services
    parameter_service = ParameterService()
    lora_resolution_service = LoRAResolutionService(store)
    lora_sync_service = LoRASyncService(
        minio_service=deps.minio_service, google_drive_service=deps.google_drive_service
    )

    try:
        # Prepare parameters dict
        parameters = {
            "num_images": request.num_images,
            "prompt": request.prompt,
            "lora_character": request.lora_character,
            "lora_custom": request.lora_custom,
            "additional_params": request.additional_params or {},
        }

        # Validate parameters against schema
        try:
            validated_params = parameter_service.validate_parameters(
                parameters, workflow.parameter_schema
            )
        except ParameterValidationError as e:
            raise HTTPException(status_code=400, detail=f"Parameter validation failed: {e!s}")

        # Resolve LoRAs
        resolved_loras = await lora_resolution_service.resolve_loras(
            user_id=user_id,
            lora_character=validated_params.get("lora_character"),
            lora_custom=validated_params.get("lora_custom"),
        )

        # Build lora_paths dict for substitution
        lora_paths = {}
        if resolved_loras.get("character"):
            lora_paths["character"] = resolved_loras["character"]
        if resolved_loras.get("custom"):
            lora_paths["custom"] = resolved_loras["custom"]

        # Substitute parameters in workflow JSON
        modified_workflow = parameter_service.substitute_parameters(
            workflow_json=workflow.workflow_json, parameters=validated_params, lora_paths=lora_paths
        )

        # Sync LoRAs to ComfyUI if needed
        for lora_filename in lora_paths.values():
            if lora_filename:
                await lora_sync_service.ensure_lora_synced(
                    user_id=user_id, lora_filename=lora_filename
                )

        # Execute workflow
        comfyui_service = ComfyUIService(
            http_client=deps.comfyui_http_client,
            base_url=deps.comfyui_url,
            lora_sync_service=lora_sync_service,
        )

        comfyui_request_id = await comfyui_service.submit_workflow(
            workflow_json=modified_workflow, user_id=user_id
        )

        if not comfyui_request_id:
            raise HTTPException(status_code=500, detail="Failed to submit workflow to ComfyUI")

        # Create workflow run record
        workflow_run = await store.create_workflow_run(
            workflow_id=workflow_id,
            user_id=user_id,
            comfyui_request_id=comfyui_request_id,
            input_params=validated_params,
        )

        # Note: Image storage and Immich upload will happen asynchronously
        # when polling for workflow completion (in get_workflow_run endpoint)

        return workflow_run

    except HTTPException:
        raise


@router.get("/workflows/{workflow_id}/runs", response_model=ListWorkflowRunsResponse)
async def list_workflow_runs(
    workflow_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """List workflow runs for a workflow."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        runs = await store.list_workflow_runs(
            user_id=user_id, workflow_id=workflow_id, limit=limit, offset=offset
        )
        return ListWorkflowRunsResponse(runs=runs, count=len(runs))
    except HTTPException:
        raise


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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
                minio_service=deps.minio_service, google_drive_service=deps.google_drive_service
            )
            comfyui_service = ComfyUIService(
                http_client=deps.comfyui_http_client,
                base_url=deps.comfyui_url,
                lora_sync_service=lora_sync_service,
            )

            status = await comfyui_service.get_job_status(run.comfyui_request_id)
            if status:
                # Update run status
                new_status = status.get("status", run.status)
                output_images = status.get("output_images", [])
                error_message = status.get("error")

                # If workflow completed, download images, store in MinIO, and upload to Immich
                minio_image_paths = []
                if new_status == "completed" and output_images and not run.output_images:
                    try:
                        # Get Immich user credentials from Supabase
                        pool = await deps.supabase_service._get_pool()
                        async with pool.acquire() as conn:
                            row = await conn.fetchrow(
                                "SELECT immich_user_id, immich_api_key, email FROM profiles WHERE id = $1",
                                user_id,
                            )
                            immich_user_id = row.get("immich_user_id") if row else None
                            immich_api_key = row.get("immich_api_key") if row else None
                            user_email = row.get("email") if row else user.email

                        # Initialize Immich service if credentials exist
                        immich_service = None
                        immich_base_url = os.getenv(
                            "IMMICH_SERVER_URL", "http://immich-server:2283"
                        )
                        immich_admin_key = os.getenv("IMMICH_API_KEY")

                        if immich_api_key:
                            immich_service = ImmichService(
                                base_url=immich_base_url, admin_api_key=immich_admin_key
                            )
                        elif immich_admin_key:
                            # Try to get or create Immich user
                            immich_service = ImmichService(
                                base_url=immich_base_url, admin_api_key=immich_admin_key
                            )
                            immich_user = await immich_service.get_or_create_user(user_email)
                            if immich_user:
                                immich_api_key = immich_user.get("apiKey")
                                immich_user_id = immich_user.get("id")
                                # Store in Supabase
                                async with pool.acquire() as conn2:
                                    await conn2.execute(
                                        "UPDATE profiles SET immich_user_id = $1, immich_api_key = $2 WHERE id = $3",
                                        immich_user_id,
                                        immich_api_key,
                                        user_id,
                                    )

                        # Download and store images
                        for idx, image_url in enumerate(output_images):
                            # Download image from ComfyUI
                            image_data = await comfyui_service.download_image(image_url)
                            if image_data:
                                filename = f"workflow_{run_id}_{idx}.png"

                                # Store in MinIO
                                minio_path = await deps.minio_service.upload_file(
                                    user_id=user_id,
                                    file_data=image_data,
                                    object_key=f"comfyui-outputs/{run_id}/{filename}",
                                    content_type="image/png",
                                )
                                minio_image_paths.append(minio_path)

                                # Upload to Immich if service is available
                                if immich_service and immich_api_key:
                                    try:
                                        description = (
                                            f"ComfyUI workflow run {run_id} - Image {idx + 1}"
                                        )
                                        await immich_service.upload_image(
                                            image_data=image_data,
                                            filename=filename,
                                            api_key=immich_api_key,
                                            description=description,
                                        )
                                        logger.info(
                                            f"Uploaded image {idx + 1} to Immich for user {user_id}"
                                        )
                                    except Exception as e:
                                        logger.error(f"Failed to upload image to Immich: {e}")

                        if immich_service:
                            await immich_service.close()
                    except Exception as e:
                        logger.error(f"Failed to process workflow images: {e}")

                # Update run with status and image paths
                updated_run = await store.update_workflow_run(
                    run_id=run_id,
                    user_id=user_id,
                    status=new_status,
                    output_images=minio_image_paths if minio_image_paths else output_images,
                    error_message=error_message,
                )

                if updated_run:
                    return updated_run

        return run

    except HTTPException:
        raise


# LoRA model endpoints


@router.post("/loras", response_model=LoRAModelResponse)
async def create_lora_model(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    file: UploadFile = File(...),
    name: str | None = None,
    description: str | None = None,
    tags: list | None = None,
    character_name: str | None = None,
    user: User = Depends(get_current_user),
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
            content_type=file.content_type,
        )
    except HTTPException:
        raise

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
            tags=tags or [],
            character_name=character_name,
        )
        return lora_model
    except HTTPException:
        raise


@router.post("/loras/import-from-google-drive", response_model=LoRAModelResponse)
async def import_lora_from_google_drive(
    request: ImportLoRAFromGoogleDriveRequest,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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
        minio_service=deps.minio_service, google_drive_service=deps.google_drive_service
    )

    try:
        # Get file metadata from Google Drive
        file_metadata = deps.google_drive_service.api.get_file_metadata(
            request.google_drive_file_id, fields="id,name,size"
        )

        filename = request.name or file_metadata.get("name", "lora.safetensors")
        file_size = file_metadata.get("size")

        # Download from Google Drive
        logger.info(
            f"Downloading LoRA from Google Drive: {request.google_drive_file_id} for user {user_id}"
        )
        file_data = deps.google_drive_service.download_file(request.google_drive_file_id)

        # Upload to MinIO
        minio_path = await deps.minio_service.upload_file(
            user_id=user_id,
            file_data=file_data,
            object_key=f"loras/{filename}",
            content_type="application/octet-stream",
        )

        # Create metadata in Supabase
        lora_model = await store.create_lora_model(
            user_id=user_id,
            name=request.name or filename,
            filename=filename,
            minio_path=minio_path,
            file_size=file_size or len(file_data),
            description=request.description,
            tags=request.tags or [],
            character_name=request.character_name,
        )

        logger.info(f"Imported LoRA from Google Drive: {filename} for user {user_id}")
        return lora_model

    except ValueError as e:
        logger.error(f"Failed to import LoRA from Google Drive: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to import LoRA: {e!s}")


@router.get("/loras", response_model=ListLoRAModelsResponse)
async def list_lora_models(
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
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
    except HTTPException:
        raise


@router.get("/loras/by-character/{character_name}", response_model=ListLoRAModelsResponse)
async def list_loras_by_character(
    character_name: str,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
):
    """Get LoRAs by character name (user-scoped)."""
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    store = SupabaseWorkflowStore(deps.supabase_service)

    try:
        models = await store.list_lora_models_by_character(
            user_id=user_id, character_name=character_name, limit=limit, offset=offset
        )
        return ListLoRAModelsResponse(models=models, count=len(models))
    except HTTPException:
        raise


@router.get("/loras/{lora_id}", response_model=LoRAModelResponse)
async def get_lora_model(
    lora_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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


@router.delete("/loras/{lora_id}")
async def delete_lora_model(
    lora_id: UUID,
    deps: Annotated[ComfyUIWorkflowDeps, Depends(get_comfyui_workflow_deps)],
    user: User = Depends(get_current_user),
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
