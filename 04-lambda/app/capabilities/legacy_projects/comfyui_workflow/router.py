"""FastAPI router for ComfyUI Workflow endpoints."""

import asyncio
import logging
import os
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.services.auth.config import AuthConfig
from app.services.auth.dependencies import get_current_user
from app.services.auth.models import User
from app.services.external.immich.client import ImmichService
from app.services.storage.minio.client import MinIOClient
from app.services.storage.minio.config import MinIOConfig

from .models import (
    AvailableLorAsResponse,
    CreateVersionRequest,
    ExportWorkflowResponse,
    GenerateWithLoraRequest,
    ImportWorkflowRequest,
    LoRAListResponse,
    LoRAModelResponse,
    NativeWorkflowInfo,
    RunStatus,
    SystemLoraInfo,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowUpdate,
    WorkflowVersionListResponse,
)
from .service import ComfyUIWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter()

# Cached singleton instances
_minio_client: MinIOClient | None = None
_immich_service: ImmichService | None = None
_db_pool: asyncpg.Pool | None = None
_service: ComfyUIWorkflowService | None = None


def get_minio_client() -> MinIOClient | None:
    """Get MinIO client instance (singleton)."""
    global _minio_client
    if _minio_client is None:
        try:
            config = MinIOConfig()
            _minio_client = MinIOClient(config)
            logger.info(
                f"Initialized MinIO client for ComfyUI workflow storage "
                f"(endpoint: {config.endpoint}, bucket: {config.bucket_name})"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize MinIO client: {e}")
            return None
    return _minio_client


def get_immich_service() -> ImmichService | None:
    """Get Immich service instance (singleton)."""
    global _immich_service
    if _immich_service is None:
        try:
            config = AuthConfig()
            if config.immich_base_url and config.immich_admin_api_key:
                _immich_service = ImmichService(config)
                logger.info(f"Initialized Immich service (url: {config.immich_base_url})")
            else:
                logger.info("Immich not configured, skipping Immich uploads")
        except Exception as e:
            logger.warning(f"Failed to initialize Immich service: {e}")
            return None
    return _immich_service


async def get_db_pool() -> asyncpg.Pool:
    """Get database pool (singleton)."""
    global _db_pool
    if _db_pool is None:
        database_url = os.getenv(
            "SUPABASE_DB_URL",
            os.getenv("DATABASE_URL", "postgresql://postgres:postgres@supabase-db:5432/postgres"),
        )
        _db_pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=10,
        )
        logger.info("Initialized database pool for ComfyUI workflow service")
    return _db_pool


async def get_service() -> ComfyUIWorkflowService:
    """Get ComfyUI workflow service instance with storage dependencies (singleton)."""
    global _service
    if _service is None:
        pool = await get_db_pool()
        _service = ComfyUIWorkflowService(
            pool=pool,
            minio_client=get_minio_client(),
            immich_service=get_immich_service(),
        )
        logger.info("Initialized ComfyUI workflow service")
    return _service


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreate,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Create a new ComfyUI workflow."""
    return await service.create_workflow(user.uid, workflow_data)


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include_public: bool = Query(True),
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """List workflows for the current user."""
    return await service.list_workflows(user.uid, page, per_page, include_public)


# Note: /workflows/native MUST come before /workflows/{workflow_id} to avoid UUID parsing
@router.get("/workflows/native", response_model=list[NativeWorkflowInfo])
async def list_native_workflows(
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """List workflows in ComfyUI's native directory."""
    return await service.list_native_workflows(user.uid)


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Get a specific workflow."""
    workflow = await service.get_workflow(workflow_id, user.uid)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    update_data: WorkflowUpdate,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Update a workflow."""
    workflow = await service.update_workflow(workflow_id, user.uid, update_data)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
    return workflow


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Delete a workflow."""
    success = await service.delete_workflow(workflow_id, user.uid)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
    return {"status": "deleted"}


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: UUID,
    run_request: WorkflowRunRequest | None = None,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Execute a workflow.

    Output images are automatically uploaded to MinIO (user-isolated storage).
    If upload_to_immich=True (default), images are also uploaded to the user's Immich library.
    """
    upload_to_immich = run_request.upload_to_immich if run_request else True
    # immich_api_key is stored in user.__dict__ during JIT provisioning
    immich_api_key = user.__dict__.get("immich_api_key")
    run = await service.execute_workflow(
        workflow_id,
        user.uid,
        run_request.input_params if run_request else None,
        upload_to_immich=upload_to_immich,
        immich_api_key=immich_api_key,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
    return run


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_run_status(
    run_id: UUID,
    check_comfyui: bool = Query(True),
    upload_to_immich: bool = Query(True),
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Get the status of a workflow run.

    If the run completes on this check, images are uploaded to MinIO and optionally Immich.
    """
    # immich_api_key is stored in user.__dict__ during JIT provisioning
    immich_api_key = user.__dict__.get("immich_api_key")
    run = await service.get_run_status(
        run_id,
        user.uid,
        check_comfyui,
        upload_to_immich=upload_to_immich,
        immich_api_key=immich_api_key,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or not authorized")
    return run


# ========== Version Management Endpoints ==========


@router.get("/workflows/{workflow_group_id}/versions", response_model=WorkflowVersionListResponse)
async def list_versions(
    workflow_group_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """List all versions of a workflow."""
    result = await service.list_versions(workflow_group_id, user.uid)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return result


@router.post("/workflows/{workflow_group_id}/versions", response_model=WorkflowResponse)
async def create_version(
    workflow_group_id: UUID,
    request: CreateVersionRequest,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Create a new version of an existing workflow."""
    try:
        return await service.create_version(
            workflow_group_id=workflow_group_id,
            user_id=user.uid,
            workflow_json=request.workflow_json,
            version_notes=request.version_notes,
            pin_new_version=request.pin_new_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workflows/{workflow_id}/pin", response_model=WorkflowResponse)
async def pin_version(
    workflow_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Pin this version as the active version for execution."""
    result = await service.pin_version(workflow_id, user.uid)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
    return result


@router.post("/workflows/group/{workflow_group_id}/run", response_model=WorkflowRunResponse)
async def run_pinned_workflow(
    workflow_group_id: UUID,
    run_request: WorkflowRunRequest | None = None,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Execute the pinned (active) version of a workflow.

    Output images are automatically uploaded to MinIO (user-isolated storage).
    If upload_to_immich=True (default), images are also uploaded to the user's Immich library.
    """
    upload_to_immich = run_request.upload_to_immich if run_request else True
    # immich_api_key is stored in user.__dict__ during JIT provisioning
    immich_api_key = user.__dict__.get("immich_api_key")
    run = await service.execute_pinned_workflow(
        workflow_group_id,
        user.uid,
        run_request.input_params if run_request else None,
        upload_to_immich=upload_to_immich,
        immich_api_key=immich_api_key,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found or no pinned version")
    return run


# ========== ComfyUI File System Integration ==========


@router.post("/workflows/{workflow_id}/export", response_model=ExportWorkflowResponse)
async def export_to_comfyui(
    workflow_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Export a workflow to ComfyUI's file system for visual editing."""
    try:
        result = await service.export_to_comfyui(workflow_id, user.uid)
        if not result:
            raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/import", response_model=WorkflowResponse)
async def import_from_comfyui(
    request: ImportWorkflowRequest,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Import a workflow from ComfyUI's file system.

    If workflow_group_id is provided, imports as a new version of that workflow.
    Otherwise, creates a new workflow.
    """
    try:
        return await service.import_from_comfyui(
            filename=request.filename,
            user_id=user.uid,
            workflow_group_id=request.workflow_group_id,
            version_notes=request.version_notes,
            pin_new_version=request.pin_new_version,
            name=request.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== LoRA Management ==========


@router.get("/loras", response_model=LoRAListResponse)
async def list_loras(
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """List LoRA models for the current user."""
    return await service.list_loras(user.uid)


@router.get("/loras/{filename}", response_model=LoRAModelResponse)
async def get_lora(
    filename: str,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Get a specific LoRA model by filename."""
    lora = await service.get_lora_by_filename(user.uid, filename)
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA model not found")
    return lora


@router.get("/loras-available", response_model=AvailableLorAsResponse)
async def list_available_loras(
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """List all available LoRAs (system + user).

    System LoRAs are available to all authenticated users.
    User LoRAs are specific to the authenticated user.
    """
    # Get system LoRAs
    system_loras_data = service.get_system_loras()
    system_loras = [
        SystemLoraInfo(
            filename=lora.get("name", ""),
            description=lora.get("description"),
            base_model=lora.get("base_model"),
            source=lora.get("source"),
        )
        for lora in system_loras_data
    ]

    # Get user LoRAs
    user_loras_response = await service.list_loras(user.uid)

    return AvailableLorAsResponse(
        system_loras=system_loras,
        user_loras=user_loras_response.models,
    )


# ========== LoRA Image Generation ==========


@router.post("/generate-with-lora", response_model=WorkflowRunResponse, status_code=202)
async def generate_with_lora(
    request: GenerateWithLoraRequest,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Generate an image using a workflow template with LoRA and prompt optimization.

    Returns immediately with HTTP 202 Accepted and a run_id.
    The actual generation happens in a background task.

    Poll GET /runs/{run_id} to track progress, or use GET /runs/{run_id}/stream for SSE updates.

    Progress states:
    - pending: Run created, not yet started
    - rewriting_prompt: Optimizing prompt with AI
    - submitting: Submitting workflow to ComfyUI
    - generating: ComfyUI is generating images
    - uploading: Uploading images to storage (images_completed shows progress)
    - completed: All done
    - failed: Error occurred (check error_message)

    The response includes:
    - progress_message: Human-readable status
    - images_completed / images_total: Progress during upload phase
    - optimized_prompt: The enhanced prompt (if optimize_prompt=true)
    - immich_asset_ids: Images appear here progressively as they upload

    The workflow template must include `_metadata.parameter_overrides` to define
    which nodes receive the substituted values.
    """
    # immich_api_key is stored in user.__dict__ during JIT provisioning
    immich_api_key = user.__dict__.get("immich_api_key")

    try:
        run = await service.generate_with_lora(
            workflow_id=request.workflow_id,
            user_id=user.uid,
            prompt=request.prompt,
            character_lora=request.character_lora,
            style_lora=request.style_lora,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            seed=request.seed,
            batch_size=request.batch_size,
            optimize_prompt=request.optimize_prompt,
            upload_to_immich=request.upload_to_immich,
            immich_api_key=immich_api_key,
        )
        if not run:
            raise HTTPException(status_code=404, detail="Workflow not found or not authorized")
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/runs/{run_id}/stream")
async def stream_run_status(
    run_id: UUID,
    user: User = Depends(get_current_user),
    service: ComfyUIWorkflowService = Depends(get_service),
):
    """Stream workflow run status updates via Server-Sent Events (SSE).

    This endpoint provides real-time status updates without polling.
    The stream ends when the run reaches a terminal state (completed or failed).

    Example client usage (JavaScript):
    ```javascript
    const eventSource = new EventSource('/api/v1/comfyui/runs/{run_id}/stream');
    eventSource.onmessage = (event) => {
        const status = JSON.parse(event.data);
        console.log(`Status: ${status.status} - ${status.progress_message}`);
        if (status.status === 'completed' || status.status === 'failed') {
            eventSource.close();
        }
    };
    ```

    Example client usage (Python):
    ```python
    import sseclient
    import requests

    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)
    for event in client.events():
        status = json.loads(event.data)
        print(f"Status: {status['status']} - {status['progress_message']}")
    ```
    """

    async def event_generator():
        """Generate SSE events with status updates."""
        last_status = None
        poll_interval = 1  # Check every second

        while True:
            try:
                # Get current status (don't trigger ComfyUI check - background task handles that)
                run = await service.get_run_status(
                    run_id, user.uid, check_comfyui=False, upload_to_immich=False
                )

                if not run:
                    yield "data: {'error': 'Run not found'}\n\n"
                    break

                # Only send update if status changed or progress changed
                current_status = (
                    run.status,
                    run.progress_message,
                    run.images_completed,
                    len(run.immich_asset_ids),
                )
                if current_status != last_status:
                    last_status = current_status
                    yield f"data: {run.model_dump_json()}\n\n"

                # Check for terminal state
                if run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                    break

                await asyncio.sleep(poll_interval)

            except Exception:
                logger.exception("Error streaming run status")
                yield "data: {'error': 'Internal error'}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/generate-from-reference", status_code=202)
async def generate_from_reference(
    image_url: str,
    prompt_description: str,
    character_lora: str,
    use_controlnet: bool = True,
    auto_select_skeleton: bool = True,
    skeleton_search_query: str | None = None,
    preprocessor_type: str | None = None,
    user: User = Depends(get_current_user),
) -> dict:
    """
    Generate images from a reference image using ControlNet

    This endpoint orchestrates:
    1. Image analysis with vision model
    2. Semantic skeleton search (if auto_select_skeleton=True)
    3. ControlNet-guided image generation with specified LoRA

    Args:
        image_url: URL of reference image
        prompt_description: Description/context for generation (e.g., "Alix sends selfie from car")
        character_lora: Character LoRA name to use
        use_controlnet: Whether to use ControlNet guidance
        auto_select_skeleton: Automatically search for matching skeleton
        skeleton_search_query: Custom query for skeleton search (uses prompt_description if None)
        preprocessor_type: Specific preprocessor to use (auto-detected if None)

    Returns:
        Job info with run_id for tracking progress via /runs/{run_id}/stream
    """
    service = await get_service()

    try:
        # Import dependencies
        from app.capabilities.legacy_projects.controlnet_skeleton.dependencies import get_skeleton_service

        skeleton_service = get_skeleton_service()

        # Step 1: Analyze reference image
        logger.info(f"Analyzing reference image: {image_url}")
        image_data = await skeleton_service.download_image_from_url(image_url)
        vision_analysis = await skeleton_service.vision_service.analyze_image(
            image_data, context=prompt_description
        )
        logger.info(f"Vision analysis: {vision_analysis.description[:100]}...")

        # Step 2: Generate optimized prompt
        from app.capabilities.legacy_projects.controlnet_skeleton.vision_service import VisionAnalysisService

        vision_service_instance = VisionAnalysisService()
        optimized_prompt = await vision_service_instance.generate_prompt_from_analysis(
            vision_analysis, character_lora=character_lora
        )
        logger.info(f"Generated prompt: {optimized_prompt[:100]}...")

        # Step 3: Find matching skeleton if requested
        skeleton = None
        if use_controlnet and auto_select_skeleton:
            from app.capabilities.legacy_projects.controlnet_skeleton.models import SkeletonSearchRequest

            search_query = skeleton_search_query or prompt_description
            logger.info(f"Searching for skeleton: {search_query}")

            search_request = SkeletonSearchRequest(
                query=search_query,
                match_count=1,
                search_type="hybrid",
                preprocessor_type=preprocessor_type,
            )

            search_results = await skeleton_service.search_skeletons(user, search_request)

            if search_results.results:
                skeleton = search_results.results[0].skeleton
                logger.info(
                    f"Selected skeleton: {skeleton.name} (similarity: {search_results.results[0].similarity_score:.2f})"
                )
            else:
                logger.warning("No matching skeletons found, proceeding without ControlNet")
                use_controlnet = False

        # Step 4: Execute generation
        # TODO: Implement actual workflow execution with skeleton injection
        # For now, return job info
        import uuid

        run_id = uuid.uuid4()

        return {
            "run_id": str(run_id),
            "status": "pending",
            "message": "Generation queued (workflow execution not yet implemented)",
            "vision_analysis": vision_analysis.model_dump(),
            "optimized_prompt": optimized_prompt,
            "selected_skeleton": skeleton.model_dump() if skeleton else None,
            "stream_url": f"/api/v1/comfyui/runs/{run_id}/stream",
        }

    except Exception as e:
        logger.error(f"Failed to generate from reference: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate from reference: {str(e)}",
        )
