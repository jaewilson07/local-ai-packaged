"""Supabase store for ComfyUI workflow management."""

import json
import logging
from typing import Any
from uuid import UUID

import asyncpg

from server.projects.auth.services.supabase_service import SupabaseService
from server.projects.comfyui_workflow.models import (
    LoRAModelResponse,
    WorkflowResponse,
    WorkflowRunResponse,
)

logger = logging.getLogger(__name__)


class SupabaseWorkflowStore:
    """Store for ComfyUI workflow operations using Supabase."""

    def __init__(self, supabase_service: SupabaseService):
        """
        Initialize Supabase workflow store.

        Args:
            supabase_service: Supabase service instance
        """
        self.supabase_service = supabase_service

    async def _get_pool(self):
        """Get database connection pool."""
        return await self.supabase_service._get_pool()

    # Workflow CRUD operations

    async def create_workflow(
        self,
        user_id: UUID,
        name: str,
        workflow_json: dict[str, Any],
        description: str | None = None,
        is_public: bool = False,
        tags: list[str] | None = None,
        parameter_schema: dict[str, Any] | None = None,
        status: str = "draft",
    ) -> WorkflowResponse:
        """
        Create a new workflow.

        Args:
            user_id: User UUID
            name: Workflow name
            workflow_json: ComfyUI workflow JSON
            description: Optional description
            is_public: Whether workflow is public
            tags: Optional tags

        Returns:
            Created workflow
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO comfyui_workflows (user_id, name, description, workflow_json, is_public, tags, parameter_schema, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                user_id,
                name,
                description,
                json.dumps(workflow_json),
                is_public,
                tags or [],
                json.dumps(parameter_schema) if parameter_schema else None,
                status,
            )

            return self._row_to_workflow(row)

    async def get_workflow(self, workflow_id: UUID, user_id: UUID) -> WorkflowResponse | None:
        """
        Get a workflow by ID (with access check).

        Args:
            workflow_id: Workflow UUID
            user_id: User UUID (for access check)

        Returns:
            Workflow if found and accessible, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflows
                WHERE id = $1 AND (user_id = $2 OR is_public = true)
                """,
                workflow_id,
                user_id,
            )

            if not row:
                return None

            return self._row_to_workflow(row)

    async def list_workflows(
        self,
        user_id: UUID,
        is_public: bool | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowResponse]:
        """
        List workflows for a user.

        Args:
            user_id: User UUID
            is_public: Filter by public status (None = all)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of workflows
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            conditions = ["(user_id = $1 OR is_public = true)"]
            params = [user_id]
            param_num = 2

            if is_public is not None:
                conditions.append(f"is_public = ${param_num}")
                params.append(is_public)
                param_num += 1

            if status is not None:
                conditions.append(f"status = ${param_num}")
                params.append(status)
                param_num += 1

            where_clause = " AND ".join(conditions)
            params.extend([limit, offset])

            rows = await conn.fetch(
                f"""
                SELECT * FROM comfyui_workflows
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_num} OFFSET ${param_num + 1}
                """,
                *params,
            )

            return [self._row_to_workflow(row) for row in rows]

    async def list_published_workflows(
        self, limit: int = 100, offset: int = 0, tags: list[str] | None = None
    ) -> list[WorkflowResponse]:
        """
        List all published workflows (available to all users).

        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            tags: Optional tags to filter by

        Returns:
            List of published workflows
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if tags:
                # Filter by tags (workflow must have at least one matching tag)
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflows
                    WHERE status = 'published'
                    AND tags && $1
                    ORDER BY published_at DESC NULLS LAST, created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    tags,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflows
                    WHERE status = 'published'
                    ORDER BY published_at DESC NULLS LAST, created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )

            return [self._row_to_workflow(row) for row in rows]

    async def publish_workflow(self, workflow_id: UUID, user_id: UUID) -> WorkflowResponse | None:
        """
        Publish a workflow (set status to 'published').

        Args:
            workflow_id: Workflow UUID
            user_id: User UUID (for ownership check)

        Returns:
            Updated workflow if found and owned, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE comfyui_workflows
                SET status = 'published', published_at = NOW(), updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                RETURNING *
                """,
                workflow_id,
                user_id,
            )

            if not row:
                return None

            return self._row_to_workflow(row)

    async def unpublish_workflow(self, workflow_id: UUID, user_id: UUID) -> WorkflowResponse | None:
        """
        Unpublish a workflow (set status to 'draft').

        Args:
            workflow_id: Workflow UUID
            user_id: User UUID (for ownership check)

        Returns:
            Updated workflow if found and owned, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE comfyui_workflows
                SET status = 'draft', updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                RETURNING *
                """,
                workflow_id,
                user_id,
            )

            if not row:
                return None

            return self._row_to_workflow(row)

    async def update_workflow(
        self,
        workflow_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None,
        workflow_json: dict[str, Any] | None = None,
        is_public: bool | None = None,
        tags: list[str] | None = None,
        parameter_schema: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> WorkflowResponse | None:
        """
        Update a workflow (with ownership check).

        Args:
            workflow_id: Workflow UUID
            user_id: User UUID (for ownership check)
            name: Optional new name
            description: Optional new description
            workflow_json: Optional new workflow JSON
            is_public: Optional new public status
            tags: Optional new tags

        Returns:
            Updated workflow if found and owned, None otherwise
        """
        pool = await self._get_pool()

        # Build update query dynamically
        updates = []
        values = []
        param_num = 1

        if name is not None:
            updates.append(f"name = ${param_num}")
            values.append(name)
            param_num += 1

        if description is not None:
            updates.append(f"description = ${param_num}")
            values.append(description)
            param_num += 1

        if workflow_json is not None:
            updates.append(f"workflow_json = ${param_num}")
            values.append(json.dumps(workflow_json))
            param_num += 1

        if is_public is not None:
            updates.append(f"is_public = ${param_num}")
            values.append(is_public)
            param_num += 1

        if tags is not None:
            updates.append(f"tags = ${param_num}")
            values.append(tags)
            param_num += 1

        if parameter_schema is not None:
            updates.append(f"parameter_schema = ${param_num}")
            values.append(json.dumps(parameter_schema))
            param_num += 1

        if status is not None:
            updates.append(f"status = ${param_num}")
            values.append(status)
            if status == "published":
                # Set published_at when publishing
                updates.append("published_at = NOW()")
            param_num += 1

        if not updates:
            # No updates, just return existing workflow
            return await self.get_workflow(workflow_id, user_id)

        # Add workflow_id and user_id for WHERE clause
        values.extend([workflow_id, user_id])

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE comfyui_workflows
                SET {", ".join(updates)}, updated_at = NOW()
                WHERE id = ${param_num} AND user_id = ${param_num + 1}
                RETURNING *
                """,
                *values,
            )

            if not row:
                return None

            return self._row_to_workflow(row)

    async def delete_workflow(self, workflow_id: UUID, user_id: UUID) -> bool:
        """
        Delete a workflow (with ownership check).

        Args:
            workflow_id: Workflow UUID
            user_id: User UUID (for ownership check)

        Returns:
            True if deleted, False if not found or not owned
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM comfyui_workflows
                WHERE id = $1 AND user_id = $2
                """,
                workflow_id,
                user_id,
            )

            return result == "DELETE 1"

    # Workflow run operations

    async def create_workflow_run(
        self,
        workflow_id: UUID | None,
        user_id: UUID,
        comfyui_request_id: str | None = None,
        input_params: dict[str, Any] | None = None,
    ) -> WorkflowRunResponse:
        """
        Create a new workflow run.

        Args:
            workflow_id: Optional workflow UUID
            user_id: User UUID
            comfyui_request_id: Optional ComfyUI request ID
            input_params: Optional input parameters

        Returns:
            Created workflow run
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO comfyui_workflow_runs (workflow_id, user_id, comfyui_request_id, status, input_params)
                VALUES ($1, $2, $3, 'pending', $4)
                RETURNING *
                """,
                workflow_id,
                user_id,
                comfyui_request_id,
                json.dumps(input_params) if input_params else None,
            )

            return self._row_to_workflow_run(row)

    async def update_workflow_run(
        self,
        run_id: UUID,
        user_id: UUID,
        status: str | None = None,
        output_images: list[str] | None = None,
        error_message: str | None = None,
    ) -> WorkflowRunResponse | None:
        """
        Update a workflow run.

        Args:
            run_id: Run UUID
            user_id: User UUID (for access check)
            status: Optional new status
            output_images: Optional output images
            error_message: Optional error message

        Returns:
            Updated workflow run if found, None otherwise
        """
        pool = await self._get_pool()

        updates = []
        values = []
        param_num = 1

        if status is not None:
            updates.append(f"status = ${param_num}")
            values.append(status)
            param_num += 1

        if output_images is not None:
            updates.append(f"output_images = ${param_num}")
            values.append(output_images)
            param_num += 1

        if error_message is not None:
            updates.append(f"error_message = ${param_num}")
            values.append(error_message)
            param_num += 1

        if status in ("completed", "failed"):
            updates.append("completed_at = NOW()")

        if not updates:
            # No updates, just return existing run
            return await self.get_workflow_run(run_id, user_id)

        values.extend([run_id, user_id])

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE comfyui_workflow_runs
                SET {", ".join(updates)}
                WHERE id = ${param_num} AND user_id = ${param_num + 1}
                RETURNING *
                """,
                *values,
            )

            if not row:
                return None

            return self._row_to_workflow_run(row)

    async def get_workflow_run(self, run_id: UUID, user_id: UUID) -> WorkflowRunResponse | None:
        """
        Get a workflow run by ID.

        Args:
            run_id: Run UUID
            user_id: User UUID (for access check)

        Returns:
            Workflow run if found, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_workflow_runs
                WHERE id = $1 AND user_id = $2
                """,
                run_id,
                user_id,
            )

            if not row:
                return None

            return self._row_to_workflow_run(row)

    async def list_workflow_runs(
        self, user_id: UUID, workflow_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[WorkflowRunResponse]:
        """
        List workflow runs for a user.

        Args:
            user_id: User UUID
            workflow_id: Optional workflow UUID to filter by
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of workflow runs
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            if workflow_id:
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflow_runs
                    WHERE user_id = $1 AND workflow_id = $2
                    ORDER BY started_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    user_id,
                    workflow_id,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM comfyui_workflow_runs
                    WHERE user_id = $1
                    ORDER BY started_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    limit,
                    offset,
                )

            return [self._row_to_workflow_run(row) for row in rows]

    # LoRA model operations

    async def create_lora_model(
        self,
        user_id: UUID,
        name: str,
        filename: str,
        minio_path: str,
        file_size: int | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        character_name: str | None = None,
    ) -> LoRAModelResponse:
        """
        Create LoRA model metadata.

        Args:
            user_id: User UUID
            name: LoRA model name
            filename: Filename in MinIO
            minio_path: Full MinIO path
            file_size: Optional file size
            description: Optional description
            tags: Optional tags

        Returns:
            Created LoRA model
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO comfyui_lora_models (user_id, name, filename, minio_path, file_size, description, tags, character_name)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                user_id,
                name,
                filename,
                minio_path,
                file_size,
                description,
                tags or [],
                character_name,
            )

            return self._row_to_lora_model(row)

    async def list_lora_models(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[LoRAModelResponse]:
        """
        List LoRA models for a user.

        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of LoRA models
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM comfyui_lora_models
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )

            return [self._row_to_lora_model(row) for row in rows]

    async def list_lora_models_by_character(
        self, user_id: UUID, character_name: str, limit: int = 100, offset: int = 0
    ) -> list[LoRAModelResponse]:
        """
        List LoRA models by character name.

        Args:
            user_id: User UUID
            character_name: Character name to search for
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of LoRA models matching character name
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM comfyui_lora_models
                WHERE user_id = $1
                AND (
                    LOWER(character_name) = LOWER($2)
                    OR $2 = ANY(SELECT LOWER(unnest(tags)))
                )
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id,
                character_name,
                limit,
                offset,
            )

            return [self._row_to_lora_model(row) for row in rows]

    async def get_lora_model(self, lora_id: UUID, user_id: UUID) -> LoRAModelResponse | None:
        """
        Get LoRA model by ID.

        Args:
            lora_id: LoRA model UUID
            user_id: User UUID (for access check)

        Returns:
            LoRA model if found, None otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM comfyui_lora_models
                WHERE id = $1 AND user_id = $2
                """,
                lora_id,
                user_id,
            )

            if not row:
                return None

            return self._row_to_lora_model(row)

    async def delete_lora_model(self, lora_id: UUID, user_id: UUID) -> bool:
        """
        Delete LoRA model metadata.

        Args:
            lora_id: LoRA model UUID
            user_id: User UUID (for ownership check)

        Returns:
            True if deleted, False if not found or not owned
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM comfyui_lora_models
                WHERE id = $1 AND user_id = $2
                """,
                lora_id,
                user_id,
            )

            return result == "DELETE 1"

    # Helper methods

    def _row_to_workflow(self, row: asyncpg.Record) -> WorkflowResponse:
        """Convert database row to WorkflowResponse."""
        return WorkflowResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            workflow_json=(
                json.loads(row["workflow_json"])
                if isinstance(row["workflow_json"], str)
                else row["workflow_json"]
            ),
            is_public=row["is_public"],
            tags=row["tags"] or [],
            status=row.get("status", "draft"),
            published_at=row.get("published_at"),
            parameter_schema=(
                json.loads(row["parameter_schema"])
                if row.get("parameter_schema") and isinstance(row["parameter_schema"], str)
                else row.get("parameter_schema")
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_workflow_run(self, row: asyncpg.Record) -> WorkflowRunResponse:
        """Convert database row to WorkflowRunResponse."""
        return WorkflowRunResponse(
            id=row["id"],
            workflow_id=row["workflow_id"],
            user_id=row["user_id"],
            comfyui_request_id=row["comfyui_request_id"],
            status=row["status"],
            input_params=(
                json.loads(row["input_params"])
                if row["input_params"] and isinstance(row["input_params"], str)
                else row["input_params"]
            ),
            output_images=row["output_images"] or [],
            error_message=row["error_message"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def _row_to_lora_model(self, row: asyncpg.Record) -> LoRAModelResponse:
        """Convert database row to LoRAModelResponse."""
        return LoRAModelResponse(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            filename=row["filename"],
            minio_path=row["minio_path"],
            file_size=row["file_size"],
            description=row["description"],
            tags=row["tags"] or [],
            character_name=row.get("character_name"),
            created_at=row["created_at"],
        )
