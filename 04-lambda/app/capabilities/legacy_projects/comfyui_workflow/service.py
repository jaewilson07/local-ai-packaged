"""ComfyUI Workflow service for business logic."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from app.services.external.immich.client import ImmichService
from app.services.storage.minio.client import MinIOClient

from .client import ComfyUIClient
from .models import (
    ExportWorkflowResponse,
    LoRAListResponse,
    LoRAModelResponse,
    NativeWorkflowInfo,
    RunStatus,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowStatus,
    WorkflowUpdate,
    WorkflowVersionListResponse,
    WorkflowVersionSummary,
)

logger = logging.getLogger(__name__)


def _row_to_workflow(row: asyncpg.Record) -> WorkflowResponse:
    """Convert a database row to WorkflowResponse."""
    return WorkflowResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        description=row.get("description"),
        workflow_json=(
            json.loads(row["workflow_json"])
            if isinstance(row["workflow_json"], str)
            else row["workflow_json"]
        ),
        is_public=row.get("is_public", False),
        tags=row.get("tags") or [],
        status=WorkflowStatus(row.get("status", "draft")),
        parameter_schema=(
            json.loads(row["parameter_schema"]) if row.get("parameter_schema") else None
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        # Versioning fields
        workflow_group_id=row.get("workflow_group_id") or row["id"],  # Fallback for old records
        version=row.get("version", 1),
        is_pinned=row.get("is_pinned", True),
        version_notes=row.get("version_notes"),
        parent_version_id=row.get("parent_version_id"),
    )


def _row_to_version_summary(row: asyncpg.Record) -> WorkflowVersionSummary:
    """Convert a database row to WorkflowVersionSummary."""
    return WorkflowVersionSummary(
        id=row["id"],
        version=row.get("version", 1),
        is_pinned=row.get("is_pinned", True),
        version_notes=row.get("version_notes"),
        created_at=row["created_at"],
    )


def _row_to_run(row: asyncpg.Record) -> WorkflowRunResponse:
    """Convert a database row to WorkflowRunResponse."""
    return WorkflowRunResponse(
        id=row["id"],
        workflow_id=row.get("workflow_id"),
        user_id=row["user_id"],
        comfyui_request_id=row.get("comfyui_request_id"),
        status=RunStatus(row.get("status", "pending")),
        input_params=json.loads(row["input_params"]) if row.get("input_params") else None,
        output_images=row.get("output_images") or [],
        minio_paths=row.get("minio_paths") or [],
        immich_asset_ids=row.get("immich_asset_ids") or [],
        error_message=row.get("error_message"),
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
        # Progress tracking fields
        progress_message=row.get("progress_message"),
        images_completed=row.get("images_completed") or 0,
        images_total=row.get("images_total"),
        optimized_prompt=row.get("optimized_prompt"),
    )


def _row_to_lora(row: asyncpg.Record) -> LoRAModelResponse:
    """Convert a database row to LoRAModelResponse."""
    return LoRAModelResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        filename=row["filename"],
        minio_path=row["minio_path"],
        file_size=row.get("file_size"),
        description=row.get("description"),
        character_name=row.get("character_name"),
        tags=row.get("tags") or [],
        version=row.get("version", 1),
        is_active=row.get("is_active", True),
        created_at=row["created_at"],
    )


class ComfyUIWorkflowService:
    """Service for managing ComfyUI workflows and execution."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        minio_client: MinIOClient | None = None,
        immich_service: ImmichService | None = None,
    ):
        self.pool = pool
        self.client = ComfyUIClient()
        self.minio_client = minio_client
        self.immich_service = immich_service

    # ========== Progress Tracking Helpers ==========

    async def _update_run_status(
        self,
        run_id: UUID,
        status: str,
        progress_message: str | None = None,
        error_message: str | None = None,
        optimized_prompt: str | None = None,
    ) -> None:
        """Update run status and progress message."""
        async with self.pool.acquire() as conn:
            if error_message:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET status = $2, progress_message = $3, error_message = $4,
                        completed_at = $5
                    WHERE id = $1
                    """,
                    run_id,
                    status,
                    progress_message,
                    error_message,
                    datetime.now(timezone.utc),
                )
            elif optimized_prompt:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET status = $2, progress_message = $3, optimized_prompt = $4
                    WHERE id = $1
                    """,
                    run_id,
                    status,
                    progress_message,
                    optimized_prompt,
                )
            else:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET status = $2, progress_message = $3
                    WHERE id = $1
                    """,
                    run_id,
                    status,
                    progress_message,
                )

    async def _update_run_progress(
        self,
        run_id: UUID,
        status: str,
        images_completed: int,
        images_total: int,
        progress_message: str | None = None,
    ) -> None:
        """Update run progress for image uploads."""
        msg = progress_message or f"Uploading images ({images_completed}/{images_total})"
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE comfyui_workflow_runs
                SET status = $2, progress_message = $3, images_completed = $4, images_total = $5
                WHERE id = $1
                """,
                run_id,
                status,
                msg,
                images_completed,
                images_total,
            )

    async def _add_immich_asset(self, run_id: UUID, asset_id: str) -> None:
        """Add a single Immich asset ID to the run's immich_asset_ids array."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE comfyui_workflow_runs
                SET immich_asset_ids = array_append(immich_asset_ids, $2)
                WHERE id = $1
                """,
                run_id,
                asset_id,
            )

    async def _add_minio_path(self, run_id: UUID, minio_path: str) -> None:
        """Add a single MinIO path to the run's minio_paths array."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE comfyui_workflow_runs
                SET minio_paths = array_append(minio_paths, $2)
                WHERE id = $1
                """,
                run_id,
                minio_path,
            )

    async def _mark_run_completed(
        self,
        run_id: UUID,
        output_images: list[str],
    ) -> None:
        """Mark a run as completed with final output images list."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE comfyui_workflow_runs
                SET status = $2, progress_message = $3, output_images = $4, completed_at = $5
                WHERE id = $1
                """,
                run_id,
                RunStatus.COMPLETED.value,
                "Completed successfully",
                output_images,
                datetime.now(timezone.utc),
            )

    async def create_workflow(
        self, user_id: UUID, workflow_data: WorkflowCreate
    ) -> WorkflowResponse:
        """Create a new workflow (v1, automatically pinned)."""
        workflow_id = uuid4()
        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO comfyui_workflows (
                    id, user_id, name, description, workflow_json,
                    is_public, tags, status, parameter_schema, created_at, updated_at,
                    workflow_group_id, version, is_pinned
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                workflow_id,
                user_id,
                workflow_data.name,
                workflow_data.description,
                json.dumps(workflow_data.workflow_json),
                workflow_data.is_public,
                workflow_data.tags,
                WorkflowStatus.DRAFT.value,
                (
                    json.dumps(workflow_data.parameter_schema)
                    if workflow_data.parameter_schema
                    else None
                ),
                now,
                now,
                workflow_id,  # workflow_group_id = id for first version
                1,  # version = 1
                True,  # is_pinned = true for first version
            )

            row = await conn.fetchrow("SELECT * FROM comfyui_workflows WHERE id = $1", workflow_id)
            return _row_to_workflow(row)

    async def get_workflow(self, workflow_id: UUID, user_id: UUID) -> WorkflowResponse | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflows
                WHERE id = $1 AND (user_id = $2 OR is_public = true)
                """,
                workflow_id,
                user_id,
            )
            return _row_to_workflow(row) if row else None

    async def list_workflows(
        self, user_id: UUID, page: int = 1, per_page: int = 20, include_public: bool = True
    ) -> WorkflowListResponse:
        offset = (page - 1) * per_page

        async with self.pool.acquire() as conn:
            if include_public:
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflows
                    WHERE user_id = $1 OR is_public = true
                    ORDER BY created_at DESC LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    per_page,
                    offset,
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM comfyui_workflows WHERE user_id = $1 OR is_public = true",
                    user_id,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflows
                    WHERE user_id = $1
                    ORDER BY created_at DESC LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    per_page,
                    offset,
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM comfyui_workflows WHERE user_id = $1",
                    user_id,
                )

            return WorkflowListResponse(
                workflows=[_row_to_workflow(row) for row in rows],
                total=total,
                page=page,
                per_page=per_page,
            )

    async def update_workflow(
        self, workflow_id: UUID, user_id: UUID, update_data: WorkflowUpdate
    ) -> WorkflowResponse | None:
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM comfyui_workflows WHERE id = $1 AND user_id = $2",
                workflow_id,
                user_id,
            )
            if not existing:
                return None

            updates = {}
            if update_data.name is not None:
                updates["name"] = update_data.name
            if update_data.description is not None:
                updates["description"] = update_data.description
            if update_data.workflow_json is not None:
                updates["workflow_json"] = json.dumps(update_data.workflow_json)
            if update_data.is_public is not None:
                updates["is_public"] = update_data.is_public
            if update_data.tags is not None:
                updates["tags"] = update_data.tags
            if update_data.status is not None:
                updates["status"] = update_data.status.value
            if update_data.parameter_schema is not None:
                updates["parameter_schema"] = json.dumps(update_data.parameter_schema)

            updates["updated_at"] = datetime.now(timezone.utc)

            if updates:
                set_clause = ", ".join([f"{k} = ${i+3}" for i, k in enumerate(updates.keys())])
                values = [workflow_id, user_id] + list(updates.values())
                await conn.execute(
                    f"UPDATE comfyui_workflows SET {set_clause} WHERE id = $1 AND user_id = $2",
                    *values,
                )

            row = await conn.fetchrow("SELECT * FROM comfyui_workflows WHERE id = $1", workflow_id)
            return _row_to_workflow(row) if row else None

    async def delete_workflow(self, workflow_id: UUID, user_id: UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM comfyui_workflows WHERE id = $1 AND user_id = $2",
                workflow_id,
                user_id,
            )
            return "DELETE 1" in result

    async def execute_workflow(
        self,
        workflow_id: UUID,
        user_id: UUID,
        input_params: dict[str, Any] | None = None,
        upload_to_immich: bool = True,
        immich_api_key: str | None = None,
    ) -> WorkflowRunResponse | None:
        async with self.pool.acquire() as conn:
            workflow_row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflows
                WHERE id = $1 AND (user_id = $2 OR is_public = true)
                """,
                workflow_id,
                user_id,
            )

            if not workflow_row:
                return None

            workflow_json = (
                json.loads(workflow_row["workflow_json"])
                if isinstance(workflow_row["workflow_json"], str)
                else workflow_row["workflow_json"]
            )
            modified_workflow = self._apply_parameter_overrides(workflow_json, input_params or {})

            run_id = uuid4()
            now = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO comfyui_workflow_runs (
                    id, workflow_id, user_id, status, input_params, started_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                run_id,
                workflow_id,
                user_id,
                RunStatus.PENDING.value,
                json.dumps(input_params) if input_params else None,
                now,
            )

            comfyui_request_id = await self.client.submit_workflow(modified_workflow)

            if comfyui_request_id:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET comfyui_request_id = $2, status = $3
                    WHERE id = $1
                    """,
                    run_id,
                    comfyui_request_id,
                    RunStatus.RUNNING.value,
                )
            else:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET status = $2, error_message = $3
                    WHERE id = $1
                    """,
                    run_id,
                    RunStatus.FAILED.value,
                    "Failed to submit workflow to ComfyUI",
                )

            row = await conn.fetchrow("SELECT * FROM comfyui_workflow_runs WHERE id = $1", run_id)
            return _row_to_run(row) if row else None

    async def get_run_status(
        self,
        run_id: UUID,
        user_id: UUID,
        check_comfyui: bool = True,
        upload_to_immich: bool = True,
        immich_api_key: str | None = None,
    ) -> WorkflowRunResponse | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM comfyui_workflow_runs WHERE id = $1 AND user_id = $2",
                run_id,
                user_id,
            )

            if not row:
                return None

            run = _row_to_run(row)

            # Check ComfyUI for both legacy RUNNING and new GENERATING status
            is_generating = run.status in (RunStatus.RUNNING, RunStatus.GENERATING)
            if check_comfyui and is_generating and run.comfyui_request_id:
                result = await self.client.get_result(run.comfyui_request_id)
                if result:
                    status = result.get("status")
                    if status == "completed":
                        run = await self._process_completion(
                            conn,
                            run_id,
                            user_id,
                            result,
                            upload_to_immich=upload_to_immich,
                            immich_api_key=immich_api_key,
                        )
                    elif status == "failed":
                        await conn.execute(
                            """
                            UPDATE comfyui_workflow_runs
                            SET status = $2, error_message = $3, completed_at = $4
                            WHERE id = $1
                            """,
                            run_id,
                            RunStatus.FAILED.value,
                            result.get("error", "Unknown error"),
                            datetime.now(timezone.utc),
                        )
                        row = await conn.fetchrow(
                            "SELECT * FROM comfyui_workflow_runs WHERE id = $1", run_id
                        )
                        run = _row_to_run(row)

            return run

    async def _process_completion(
        self,
        conn: asyncpg.Connection,
        run_id: UUID,
        user_id: UUID,
        result: dict[str, Any],
        upload_to_immich: bool = True,
        immich_api_key: str | None = None,
    ) -> WorkflowRunResponse:
        """
        Process workflow completion: download images from ComfyUI and upload to user storage.

        Images are uploaded progressively - each image is uploaded and the database
        is updated immediately, so clients can see images appear in Immich as they complete.

        Images are always uploaded to MinIO (user-isolated storage).
        Optionally uploaded to Immich if upload_to_immich=True and user has API key.
        """
        images = self.client.extract_output_images(result)
        output_images = [img["filename"] for img in images]
        total_images = len(images)

        # Update status to uploading and set expected total
        await self._update_run_progress(
            run_id, RunStatus.UPLOADING.value, 0, total_images, "Downloading images from ComfyUI..."
        )

        # Download and upload each image progressively
        for i, img_info in enumerate(images):
            filename = img_info.get("filename")
            subfolder = img_info.get("subfolder", "")
            folder_type = img_info.get("type", "output")

            if not filename:
                continue

            try:
                # Download image from ComfyUI
                image_data = await self.client.get_image(filename, subfolder, folder_type)
                if not image_data:
                    logger.warning(f"Failed to download image {filename} from ComfyUI")
                    continue

                # Upload to MinIO (always, for user-isolated storage)
                if self.minio_client:
                    try:
                        # Determine content type
                        content_type = "image/png"
                        lower_filename = filename.lower()
                        if lower_filename.endswith((".jpg", ".jpeg")):
                            content_type = "image/jpeg"
                        elif lower_filename.endswith(".webp"):
                            content_type = "image/webp"
                        elif lower_filename.endswith(".gif"):
                            content_type = "image/gif"

                        # Store in user's comfyui folder with run_id for organization
                        object_key = f"comfyui/{run_id}/{filename}"
                        minio_path = await self.minio_client.upload_file(
                            user_id=user_id,
                            file_data=image_data,
                            object_key=object_key,
                            content_type=content_type,
                            metadata={
                                "run_id": str(run_id),
                                "source": "comfyui",
                            },
                        )
                        # Progressively update MinIO paths
                        await self._add_minio_path(run_id, minio_path)
                        logger.info(f"Uploaded {filename} to MinIO: {minio_path}")
                    except Exception:
                        logger.exception(f"Failed to upload {filename} to MinIO")

                # Upload to Immich (optional, if user requested and has API key)
                # Progressive: upload immediately and update DB so image appears in Immich
                if upload_to_immich and immich_api_key and self.immich_service:
                    try:
                        asset_id = await self.immich_service.upload_asset(
                            user_api_key=immich_api_key,
                            file_data=image_data,
                            filename=filename,
                            device_asset_id=f"comfyui-{run_id}-{filename}",
                        )
                        if asset_id:
                            # Progressively update Immich asset IDs
                            await self._add_immich_asset(run_id, asset_id)
                            logger.info(f"Uploaded {filename} to Immich: {asset_id}")
                    except Exception:
                        logger.exception(f"Failed to upload {filename} to Immich")

                # Update progress after each image
                await self._update_run_progress(
                    run_id,
                    RunStatus.UPLOADING.value,
                    i + 1,
                    total_images,
                    f"Uploading images ({i + 1}/{total_images})",
                )

            except Exception:
                logger.exception(f"Error processing image {filename}")

        # Mark as completed
        await self._mark_run_completed(run_id, output_images)

        row = await conn.fetchrow("SELECT * FROM comfyui_workflow_runs WHERE id = $1", run_id)
        return _row_to_run(row)

    def _convert_ui_to_api_format(self, workflow_json: dict[str, Any]) -> dict[str, Any]:
        """
        Convert ComfyUI UI workflow format to API format.

        UI format has:
        - nodes: array of node objects with id, type, inputs, widgets_values
        - links: array of link connections

        API format has:
        - keys are node IDs
        - values have class_type and inputs (combined from connections and widget values)
        """

        # If already in API format (no 'nodes' array), return as-is
        if "nodes" not in workflow_json:
            return workflow_json

        nodes = workflow_json.get("nodes", [])
        links = workflow_json.get("links", [])

        # Build link lookup: link_id -> (source_node_id, source_slot, target_node_id, target_slot, type)
        link_lookup = {}
        for link in links:
            if len(link) >= 5:
                link_id, src_node, src_slot, dst_node, dst_slot = link[:5]
                link_type = link[5] if len(link) > 5 else "*"
                link_lookup[link_id] = (src_node, src_slot, dst_node, dst_slot, link_type)

        api_workflow = {}

        for node in nodes:
            node_id = str(node.get("id"))
            node_type = node.get("type")

            if not node_type:
                continue

            # Skip certain node types that are UI-only
            if node_type in ("Note", "Reroute"):
                continue

            node_config = {
                "class_type": node_type,
                "inputs": {},
            }

            # Get widget values (default values from UI)
            widgets_values = node.get("widgets_values", [])

            # Get input definitions from the node
            inputs = node.get("inputs", [])

            # Map inputs that come from links
            for inp in inputs:
                inp_name = inp.get("name")
                link_id = inp.get("link")

                if link_id and link_id in link_lookup:
                    src_node, src_slot, _, _, _ = link_lookup[link_id]
                    node_config["inputs"][inp_name] = [str(src_node), src_slot]

            # Add widget values as inputs
            # This requires knowing the widget order for each node type
            # For now, try to extract from the node's properties
            node_properties = node.get("properties", {})

            # Common pattern: widgets have specific names, try to infer
            # Different node types have different widget layouts
            # This is a best-effort mapping
            widget_idx = 0

            # Check for explicit widget definitions in outputs
            outputs = node.get("outputs", [])

            # Try to map widgets by type-specific patterns
            if node_type == "KSampler":
                widget_names = [
                    "seed",
                    "control_after_generate",
                    "steps",
                    "cfg",
                    "sampler_name",
                    "scheduler",
                    "denoise",
                ]
                for i, wname in enumerate(widget_names):
                    if i < len(widgets_values) and wname not in node_config["inputs"]:
                        node_config["inputs"][wname] = widgets_values[i]
            elif node_type == "EmptyLatentImage" or node_type == "EmptySD3LatentImage":
                widget_names = ["width", "height", "batch_size"]
                for i, wname in enumerate(widget_names):
                    if i < len(widgets_values) and wname not in node_config["inputs"]:
                        node_config["inputs"][wname] = widgets_values[i]
            elif node_type == "CLIPTextEncode":
                if widgets_values and "text" not in node_config["inputs"]:
                    node_config["inputs"]["text"] = widgets_values[0]
            elif node_type == "SaveImage":
                if widgets_values and "filename_prefix" not in node_config["inputs"]:
                    node_config["inputs"]["filename_prefix"] = widgets_values[0]
            elif node_type == "LoraLoader":
                widget_names = ["lora_name", "strength_model", "strength_clip"]
                for i, wname in enumerate(widget_names):
                    if i < len(widgets_values) and wname not in node_config["inputs"]:
                        node_config["inputs"][wname] = widgets_values[i]
            else:
                # Generic: try to add all widget values with numeric keys if not already mapped
                # This is a fallback and may not work for all node types
                # Skip for now as it could cause issues
                pass

            api_workflow[node_id] = node_config

        return api_workflow

    def _apply_parameter_overrides(
        self, workflow_json: dict[str, Any], params: dict[str, Any]
    ) -> dict[str, Any]:
        import copy

        modified = copy.deepcopy(workflow_json)

        metadata = modified.pop("_metadata", {})
        overrides = metadata.get("parameter_overrides", {})

        # Convert UI format to API format
        modified = self._convert_ui_to_api_format(modified)

        for param_name, param_value in params.items():
            if param_name in overrides:
                override_config = overrides[param_name]
                node_id = str(override_config.get("node_id"))
                field = override_config.get("field")
                subfield = override_config.get("subfield")

                if node_id in modified and field:
                    if subfield:
                        if field in modified[node_id]:
                            modified[node_id][field][subfield] = param_value
                    else:
                        modified[node_id][field] = param_value
            # Also try direct node ID approach for API format
            elif "prompt_node_id" in overrides and param_name == "prompt":
                node_id = str(overrides["prompt_node_id"])
                if node_id in modified:
                    modified[node_id]["inputs"]["text"] = param_value
            elif "seed_node_id" in overrides and param_name == "seed":
                node_id = str(overrides["seed_node_id"])
                if node_id in modified:
                    modified[node_id]["inputs"]["seed"] = param_value

        return modified

    # ========== Version Management Methods ==========

    async def create_version(
        self,
        workflow_group_id: UUID,
        user_id: UUID,
        workflow_json: dict[str, Any],
        version_notes: str | None = None,
        pin_new_version: bool = False,
    ) -> WorkflowResponse:
        """Create a new version of an existing workflow."""
        async with self.pool.acquire() as conn:
            # Get the current workflow info (any version in the group)
            base_workflow = await conn.fetchrow(
                """
                SELECT name, description, is_public, tags, status, parameter_schema
                FROM comfyui_workflows
                WHERE workflow_group_id = $1 AND user_id = $2
                ORDER BY version DESC
                LIMIT 1
                """,
                workflow_group_id,
                user_id,
            )

            if not base_workflow:
                raise ValueError(f"Workflow group {workflow_group_id} not found")

            # Get next version number
            next_version = await conn.fetchval(
                "SELECT get_next_workflow_version($1)",
                workflow_group_id,
            )

            # Get the current pinned version ID as parent
            parent_version_id = await conn.fetchval(
                """
                SELECT id FROM comfyui_workflows
                WHERE workflow_group_id = $1 AND user_id = $2 AND is_pinned = true
                """,
                workflow_group_id,
                user_id,
            )

            new_id = uuid4()
            now = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO comfyui_workflows (
                    id, user_id, name, description, workflow_json,
                    is_public, tags, status, parameter_schema, created_at, updated_at,
                    workflow_group_id, version, is_pinned, version_notes, parent_version_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                new_id,
                user_id,
                base_workflow["name"],
                base_workflow["description"],
                json.dumps(workflow_json),
                base_workflow["is_public"],
                base_workflow["tags"],
                base_workflow["status"],
                base_workflow["parameter_schema"],
                now,
                now,
                workflow_group_id,
                next_version,
                pin_new_version,  # Trigger will unpin others if True
                version_notes,
                parent_version_id,
            )

            row = await conn.fetchrow("SELECT * FROM comfyui_workflows WHERE id = $1", new_id)
            return _row_to_workflow(row)

    async def pin_version(self, workflow_id: UUID, user_id: UUID) -> WorkflowResponse | None:
        """Pin a specific version (unpin others in group via trigger)."""
        async with self.pool.acquire() as conn:
            # Verify ownership
            workflow = await conn.fetchrow(
                "SELECT * FROM comfyui_workflows WHERE id = $1 AND user_id = $2",
                workflow_id,
                user_id,
            )
            if not workflow:
                return None

            # Pin this version (trigger handles unpinning others)
            await conn.execute(
                """
                UPDATE comfyui_workflows
                SET is_pinned = true, updated_at = $2
                WHERE id = $1
                """,
                workflow_id,
                datetime.now(timezone.utc),
            )

            row = await conn.fetchrow("SELECT * FROM comfyui_workflows WHERE id = $1", workflow_id)
            return _row_to_workflow(row)

    async def get_pinned_workflow(
        self, workflow_group_id: UUID, user_id: UUID
    ) -> WorkflowResponse | None:
        """Get the pinned (active) version of a workflow."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflows
                WHERE workflow_group_id = $1
                  AND (user_id = $2 OR is_public = true)
                  AND is_pinned = true
                """,
                workflow_group_id,
                user_id,
            )
            return _row_to_workflow(row) if row else None

    async def list_versions(
        self, workflow_group_id: UUID, user_id: UUID
    ) -> WorkflowVersionListResponse | None:
        """List all versions of a workflow."""
        async with self.pool.acquire() as conn:
            # Get all versions
            rows = await conn.fetch(
                """
                SELECT * FROM comfyui_workflows
                WHERE workflow_group_id = $1 AND (user_id = $2 OR is_public = true)
                ORDER BY version DESC
                """,
                workflow_group_id,
                user_id,
            )

            if not rows:
                return None

            # Get pinned version number
            pinned_version = 1
            name = rows[0]["name"]
            description = rows[0].get("description")
            for row in rows:
                if row.get("is_pinned"):
                    pinned_version = row.get("version", 1)
                    break

            versions = [_row_to_version_summary(row) for row in rows]

            return WorkflowVersionListResponse(
                workflow_group_id=workflow_group_id,
                name=name,
                description=description,
                versions=versions,
                pinned_version=pinned_version,
                total_versions=len(versions),
            )

    async def execute_pinned_workflow(
        self,
        workflow_group_id: UUID,
        user_id: UUID,
        input_params: dict[str, Any] | None = None,
        upload_to_immich: bool = True,
        immich_api_key: str | None = None,
    ) -> WorkflowRunResponse | None:
        """Execute the pinned version of a workflow."""
        pinned = await self.get_pinned_workflow(workflow_group_id, user_id)
        if not pinned:
            return None
        return await self.execute_workflow(
            pinned.id,
            user_id,
            input_params,
            upload_to_immich=upload_to_immich,
            immich_api_key=immich_api_key,
        )

    # ========== File System Integration Methods ==========

    async def export_to_comfyui(
        self, workflow_id: UUID, user_id: UUID
    ) -> ExportWorkflowResponse | None:
        """Export a workflow to ComfyUI's file system for editing."""
        import re
        from pathlib import Path

        from .config import config

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM comfyui_workflows WHERE id = $1 AND user_id = $2",
                workflow_id,
                user_id,
            )
            if not row:
                return None

            workflow = _row_to_workflow(row)

            # Generate filename: db_{group_id}_{sanitized_name}_v{version}.json
            sanitized_name = re.sub(r"[^a-zA-Z0-9_-]", "_", workflow.name.lower())[:30]
            filename = f"{config.managed_workflow_prefix}{workflow.workflow_group_id}_{sanitized_name}_v{workflow.version}.json"

            # Prepare workflow JSON (strip _metadata for ComfyUI compatibility)
            export_json = workflow.workflow_json.copy()
            export_json.pop("_metadata", None)

            # Add metadata comment as a special field that ComfyUI ignores
            export_json["_export_info"] = {
                "workflow_id": str(workflow.id),
                "workflow_group_id": str(workflow.workflow_group_id),
                "version": workflow.version,
                "name": workflow.name,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }

            # Write to file system
            workflows_dir = Path(config.comfyui_workflows_dir)
            if not workflows_dir.exists():
                logger.warning(f"ComfyUI workflows directory does not exist: {workflows_dir}")
                # Try to create it
                try:
                    workflows_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    logger.error(f"Failed to create workflows directory: {e}")
                    raise ValueError(f"Cannot access ComfyUI workflows directory: {workflows_dir}")

            file_path = workflows_dir / filename
            with open(file_path, "w") as f:
                json.dump(export_json, f, indent=2)

            logger.info(f"Exported workflow {workflow_id} to {file_path}")

            return ExportWorkflowResponse(
                filename=filename,
                path=str(file_path),
                workflow_id=workflow.id,
                version=workflow.version,
            )

    async def import_from_comfyui(
        self,
        filename: str,
        user_id: UUID,
        workflow_group_id: UUID | None = None,
        version_notes: str | None = None,
        pin_new_version: bool = False,
        name: str | None = None,
    ) -> WorkflowResponse:
        """Import a workflow from ComfyUI's file system."""
        from pathlib import Path

        from .config import config

        workflows_dir = Path(config.comfyui_workflows_dir)
        file_path = workflows_dir / filename

        if not file_path.exists():
            raise ValueError(f"Workflow file not found: {filename}")

        # Read workflow JSON
        with open(file_path) as f:
            workflow_json = json.load(f)

        # Extract export info if present
        export_info = workflow_json.pop("_export_info", None)

        # Determine if this is a new workflow or a new version
        if workflow_group_id:
            # Import as new version of existing workflow
            return await self.create_version(
                workflow_group_id=workflow_group_id,
                user_id=user_id,
                workflow_json=workflow_json,
                version_notes=version_notes,
                pin_new_version=pin_new_version,
            )
        # Create new workflow
        # Try to extract name from export_info or filename
        if not name:
            if export_info and export_info.get("name"):
                name = export_info["name"]
            else:
                # Extract name from filename
                name = filename.replace(".json", "").replace("_", " ").title()

        workflow_data = WorkflowCreate(
            name=name,
            workflow_json=workflow_json,
        )
        return await self.create_workflow(user_id, workflow_data)

    async def list_native_workflows(self, user_id: UUID) -> list[NativeWorkflowInfo]:
        """List workflows in ComfyUI's native directory."""
        from pathlib import Path

        from .config import config

        workflows_dir = Path(config.comfyui_workflows_dir)
        if not workflows_dir.exists():
            return []

        result = []
        for file_path in workflows_dir.glob("*.json"):
            stat = file_path.stat()
            is_managed = file_path.name.startswith(config.managed_workflow_prefix)

            result.append(
                NativeWorkflowInfo(
                    filename=file_path.name,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    is_managed=is_managed,
                )
            )

        # Sort by modified time, newest first
        result.sort(key=lambda x: x.modified_at, reverse=True)
        return result

    async def list_loras(self, user_id: UUID) -> LoRAListResponse:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM comfyui_lora_models
                WHERE user_id = $1 AND is_active = true
                ORDER BY created_at DESC
                """,
                user_id,
            )

            return LoRAListResponse(
                models=[_row_to_lora(row) for row in rows],
                total=len(rows),
            )

    async def get_lora_by_filename(self, user_id: UUID, filename: str) -> LoRAModelResponse | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_lora_models
                WHERE user_id = $1 AND filename = $2 AND is_active = true
                """,
                user_id,
                filename,
            )
            return _row_to_lora(row) if row else None

    # ========== LoRA Validation Methods ==========

    def get_system_loras(self) -> list[dict[str, Any]]:
        """Get list of system LoRAs from known_models.yml.

        System LoRAs are available to all authenticated users.
        """
        from pathlib import Path

        import yaml

        # Try to load from known_models.yml
        known_models_paths = [
            Path("/comfyui-basedir/scripts/known_models.yml"),
            Path("02-compute/comfyui/scripts/known_models.yml"),
        ]

        for path in known_models_paths:
            if path.exists():
                try:
                    with path.open() as f:
                        models = yaml.safe_load(f)
                        return models.get("loras", [])
                except Exception as e:
                    logger.warning(f"Failed to load known_models.yml from {path}: {e}")

        # Fallback to hardcoded list of common system LoRAs
        return [
            {
                "name": "z_image_turbo_realism.safetensors",
                "description": "Ultra-realistic photos with enhanced detail",
                "base_model": "Z-Image-Turbo",
            },
            {
                "name": "amateur_photography_zimage_v1.safetensors",
                "description": "Natural candid/selfie photography look",
                "base_model": "Z-Image-Turbo",
            },
        ]

    def is_system_lora(self, filename: str) -> bool:
        """Check if a LoRA filename is a system LoRA."""
        system_loras = self.get_system_loras()
        return any(lora.get("name") == filename for lora in system_loras)

    async def validate_lora_access(
        self, user_id: UUID, lora_filename: str
    ) -> tuple[bool, str | None]:
        """Validate user access to a LoRA.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if it's a system LoRA (available to all users)
        if self.is_system_lora(lora_filename):
            return True, None

        # Check if it's a user LoRA
        user_lora = await self.get_lora_by_filename(user_id, lora_filename)
        if user_lora:
            return True, None

        return False, f"LoRA '{lora_filename}' not found or not accessible"

    async def get_lora_character_name(self, user_id: UUID, lora_filename: str) -> str | None:
        """Get the character name associated with a LoRA for trigger word preservation."""
        # Check user LoRAs first (they have character_name field)
        user_lora = await self.get_lora_by_filename(user_id, lora_filename)
        if user_lora and user_lora.character_name:
            return user_lora.character_name

        # System LoRAs don't typically have character names
        return None

    # ========== Generate With LoRA ==========

    async def generate_with_lora(
        self,
        workflow_id: UUID,
        user_id: UUID,
        prompt: str,
        character_lora: str,
        style_lora: str | None = None,
        negative_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        seed: int | None = None,
        batch_size: int = 1,
        optimize_prompt: bool = True,
        upload_to_immich: bool = True,
        immich_api_key: str | None = None,
    ) -> WorkflowRunResponse | None:
        """Generate an image using a workflow template with LoRA and prompt optimization.

        Returns immediately with a run_id. The actual generation happens in a background task.
        Clients should poll /runs/{run_id} to track progress.

        Args:
            workflow_id: UUID of the workflow template in the database
            user_id: UUID of the requesting user
            prompt: User's natural language prompt
            character_lora: Filename of the character LoRA
            style_lora: Optional filename of a style LoRA
            negative_prompt: Optional negative prompt (generated if not provided)
            width: Optional width override
            height: Optional height override
            seed: Optional seed (random if not provided)
            batch_size: Number of images to generate (1-8)
            optimize_prompt: Whether to use Ollama to enhance the prompt
            upload_to_immich: Whether to upload to Immich
            immich_api_key: User's Immich API key

        Returns:
            WorkflowRunResponse with status=pending, or None if workflow not found
        """
        import random

        # 1. Verify workflow exists
        async with self.pool.acquire() as conn:
            workflow_row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflows
                WHERE id = $1 AND (user_id = $2 OR is_public = true)
                """,
                workflow_id,
                user_id,
            )

            if not workflow_row:
                logger.warning(f"Workflow {workflow_id} not found for user {user_id}")
                return None

        # 2. Validate LoRA access (do this synchronously to fail fast)
        is_valid, error_msg = await self.validate_lora_access(user_id, character_lora)
        if not is_valid:
            logger.error(f"Character LoRA validation failed: {error_msg}")
            raise ValueError(f"Character LoRA validation failed: {error_msg}")

        if style_lora:
            is_valid, error_msg = await self.validate_lora_access(user_id, style_lora)
            if not is_valid:
                logger.error(f"Style LoRA validation failed: {error_msg}")
                raise ValueError(f"Style LoRA validation failed: {error_msg}")

        # 3. Create run record immediately (status=pending)
        run_id = uuid4()
        now = datetime.now(timezone.utc)
        generated_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

        # Store initial input params (before prompt optimization)
        initial_input_params: dict[str, Any] = {
            "original_prompt": prompt,
            "character_lora": character_lora,
            "seed": generated_seed,
        }
        if style_lora:
            initial_input_params["style_lora"] = style_lora
        if negative_prompt:
            initial_input_params["negative_prompt"] = negative_prompt
        if width:
            initial_input_params["width"] = width
        if height:
            initial_input_params["height"] = height
        if batch_size > 1:
            initial_input_params["batch_size"] = batch_size

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO comfyui_workflow_runs (
                    id, workflow_id, user_id, status, input_params, started_at,
                    progress_message, images_total
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                run_id,
                workflow_id,
                user_id,
                RunStatus.PENDING.value,
                json.dumps(initial_input_params),
                now,
                "Initializing...",
                batch_size,
            )

        # 4. Start background task for the actual generation
        asyncio.create_task(
            self._execute_generate_with_lora_background(
                run_id=run_id,
                workflow_id=workflow_id,
                user_id=user_id,
                prompt=prompt,
                character_lora=character_lora,
                style_lora=style_lora,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=generated_seed,
                batch_size=batch_size,
                optimize_prompt=optimize_prompt,
                upload_to_immich=upload_to_immich,
                immich_api_key=immich_api_key,
            )
        )

        # 5. Return immediately with the run record
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM comfyui_workflow_runs WHERE id = $1", run_id)
            return _row_to_run(row) if row else None

    async def _execute_generate_with_lora_background(
        self,
        run_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        prompt: str,
        character_lora: str,
        style_lora: str | None,
        negative_prompt: str | None,
        width: int | None,
        height: int | None,
        seed: int,
        batch_size: int,
        optimize_prompt: bool,
        upload_to_immich: bool,
        immich_api_key: str | None,
    ) -> None:
        """Background task that handles the actual LoRA generation workflow.

        Updates the run status progressively as it moves through each step.
        """
        import openai

        from app.core.config import settings

        from .prompt_rewriter import get_default_negative_prompt, rewrite_prompt_for_zimage_turbo

        try:
            # Step 1: Get character name for trigger word preservation
            character_name = await self.get_lora_character_name(user_id, character_lora)

            # Step 2: Optionally rewrite prompt using Ollama
            final_positive_prompt = prompt
            final_negative_prompt = negative_prompt or get_default_negative_prompt()

            if optimize_prompt:
                await self._update_run_status(
                    run_id,
                    RunStatus.REWRITING_PROMPT.value,
                    "Optimizing prompt with AI...",
                )
                try:
                    llm_client = openai.AsyncOpenAI(
                        base_url=settings.llm_base_url,
                        api_key=settings.llm_api_key,
                    )
                    (
                        final_positive_prompt,
                        final_negative_prompt,
                    ) = await rewrite_prompt_for_zimage_turbo(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        character_name=character_name,
                        llm_client=llm_client,
                        llm_model=settings.llm_model,
                    )
                    # Store the optimized prompt
                    await self._update_run_status(
                        run_id,
                        RunStatus.REWRITING_PROMPT.value,
                        "Prompt optimized",
                        optimized_prompt=final_positive_prompt,
                    )
                except Exception as e:
                    logger.warning(f"Prompt rewriting failed, using original: {e}")
                    # Continue with original prompt

            # Step 3: Build input_params dict for workflow execution
            input_params: dict[str, Any] = {
                "positive_prompt": final_positive_prompt,
                "negative_prompt": final_negative_prompt,
                "character_lora": character_lora,
            }

            if style_lora:
                input_params["style_lora"] = style_lora

            input_params["seed"] = seed

            if width is not None:
                input_params["width"] = width
            if height is not None:
                input_params["height"] = height
            if batch_size > 1:
                input_params["batch_size"] = batch_size

            # Step 4: Load workflow and apply parameter overrides
            await self._update_run_status(
                run_id, RunStatus.SUBMITTING.value, "Preparing workflow..."
            )

            async with self.pool.acquire() as conn:
                workflow_row = await conn.fetchrow(
                    "SELECT workflow_json FROM comfyui_workflows WHERE id = $1",
                    workflow_id,
                )

                if not workflow_row:
                    await self._update_run_status(
                        run_id,
                        RunStatus.FAILED.value,
                        "Workflow not found",
                        error_message="Workflow not found",
                    )
                    return

                workflow_json = (
                    json.loads(workflow_row["workflow_json"])
                    if isinstance(workflow_row["workflow_json"], str)
                    else workflow_row["workflow_json"]
                )

            modified_workflow = self._apply_parameter_overrides(workflow_json, input_params)

            # Step 5: Submit to ComfyUI
            await self._update_run_status(
                run_id, RunStatus.SUBMITTING.value, "Submitting to ComfyUI..."
            )

            comfyui_request_id = await self.client.submit_workflow(modified_workflow)

            if not comfyui_request_id:
                await self._update_run_status(
                    run_id,
                    RunStatus.FAILED.value,
                    "Failed to submit workflow",
                    error_message="Failed to submit workflow to ComfyUI",
                )
                return

            # Update with ComfyUI request ID
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE comfyui_workflow_runs
                    SET comfyui_request_id = $2, status = $3, progress_message = $4,
                        input_params = $5
                    WHERE id = $1
                    """,
                    run_id,
                    comfyui_request_id,
                    RunStatus.GENERATING.value,
                    "Generating images...",
                    json.dumps(input_params),
                )

            logger.info(
                f"Workflow {workflow_id} submitted with LoRA {character_lora}, "
                f"prompt: '{final_positive_prompt[:50]}...', request_id: {comfyui_request_id}"
            )

            # Step 6: Poll for completion
            result = await self.client.poll_for_completion(comfyui_request_id)

            if not result:
                await self._update_run_status(
                    run_id,
                    RunStatus.FAILED.value,
                    "Generation timed out",
                    error_message="ComfyUI workflow timed out",
                )
                return

            status = result.get("status")
            if status == "failed":
                await self._update_run_status(
                    run_id,
                    RunStatus.FAILED.value,
                    "Generation failed",
                    error_message=result.get("error", "Unknown error"),
                )
                return

            # Step 7: Process completion (progressive image uploads)
            async with self.pool.acquire() as conn:
                await self._process_completion(
                    conn,
                    run_id,
                    user_id,
                    result,
                    upload_to_immich=upload_to_immich,
                    immich_api_key=immich_api_key,
                )

        except Exception as e:
            logger.exception(f"Background generation failed for run {run_id}: {e}")
            await self._update_run_status(
                run_id,
                RunStatus.FAILED.value,
                "Generation failed",
                error_message=str(e),
            )
