"""Pydantic models for ComfyUI Workflow API."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """Granular status tracking for workflow runs."""

    PENDING = "pending"  # Initial state, run created but not started
    REWRITING_PROMPT = "rewriting_prompt"  # Optimizing prompt with Ollama
    SUBMITTING = "submitting"  # Submitting workflow to ComfyUI
    RUNNING = "running"  # Legacy status (for backwards compatibility)
    GENERATING = "generating"  # ComfyUI is generating images
    UPLOADING = "uploading"  # Uploading images to MinIO/Immich
    COMPLETED = "completed"  # All done successfully
    FAILED = "failed"  # Error occurred


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    workflow_json: dict[str, Any]
    is_public: bool = False
    tags: list[str] = Field(default_factory=list)
    parameter_schema: dict[str, Any] | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    workflow_json: dict[str, Any] | None = None
    is_public: bool | None = None
    tags: list[str] | None = None
    status: WorkflowStatus | None = None
    parameter_schema: dict[str, Any] | None = None


class WorkflowRunRequest(BaseModel):
    input_params: dict[str, Any] | None = None
    upload_to_immich: bool = True


class WorkflowResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    workflow_json: dict[str, Any]
    is_public: bool
    tags: list[str] = Field(default_factory=list)
    status: WorkflowStatus
    parameter_schema: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    # Versioning fields
    workflow_group_id: UUID
    version: int = 1
    is_pinned: bool = True
    version_notes: str | None = None
    parent_version_id: UUID | None = None

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowResponse]
    total: int
    page: int
    per_page: int


# Version management models
class WorkflowVersionSummary(BaseModel):
    """Summary of a workflow version for listing."""

    id: UUID
    version: int
    is_pinned: bool
    version_notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowVersionListResponse(BaseModel):
    """Response for listing all versions of a workflow."""

    workflow_group_id: UUID
    name: str
    description: str | None = None
    versions: list[WorkflowVersionSummary]
    pinned_version: int
    total_versions: int


class CreateVersionRequest(BaseModel):
    """Request to create a new version of an existing workflow."""

    workflow_json: dict[str, Any]
    version_notes: str | None = None
    pin_new_version: bool = False


class ImportWorkflowRequest(BaseModel):
    """Request to import a workflow from ComfyUI's file system."""

    filename: str
    workflow_group_id: UUID | None = None  # If provided, import as new version
    version_notes: str | None = None
    pin_new_version: bool = False
    name: str | None = None  # Only used when creating new workflow (no workflow_group_id)


class ExportWorkflowResponse(BaseModel):
    """Response from exporting a workflow to ComfyUI's file system."""

    filename: str
    path: str
    workflow_id: UUID
    version: int


class NativeWorkflowInfo(BaseModel):
    """Information about a workflow in ComfyUI's native directory."""

    filename: str
    size_bytes: int
    modified_at: datetime
    is_managed: bool  # True if this was exported from the database (has db_ prefix)


class WorkflowRunResponse(BaseModel):
    id: UUID
    workflow_id: UUID | None = None
    user_id: UUID
    comfyui_request_id: str | None = None
    status: RunStatus
    input_params: dict[str, Any] | None = None
    output_images: list[str] = Field(default_factory=list)
    minio_paths: list[str] = Field(default_factory=list)
    immich_asset_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    # Progress tracking fields
    progress_message: str | None = None  # Human-readable status message
    images_completed: int = 0  # Number of images uploaded so far
    images_total: int | None = None  # Expected total (from batch_size)
    optimized_prompt: str | None = None  # The enhanced prompt after LLM rewriting

    class Config:
        from_attributes = True


class LoRAModelResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    filename: str
    minio_path: str
    file_size: int | None = None
    description: str | None = None
    character_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class LoRAListResponse(BaseModel):
    models: list[LoRAModelResponse]
    total: int


class GenerateWithLoraRequest(BaseModel):
    """Request model for generating images with LoRA and prompt optimization."""

    workflow_id: UUID  # Reference to stored workflow template
    prompt: str  # User's natural language prompt
    character_lora: str  # LoRA filename (e.g., "alix_character_lora_zit.safetensors")
    style_lora: str | None = None  # Optional style LoRA
    negative_prompt: str | None = None  # Optional (generated if not provided)
    width: int | None = None  # Override workflow default
    height: int | None = None  # Override workflow default
    seed: int | None = None  # Random if not provided
    batch_size: int = Field(default=1, ge=1, le=8)  # Number of images to generate (1-8)
    optimize_prompt: bool = True  # Use Ollama to enhance prompt
    upload_to_immich: bool = True


class SystemLoraInfo(BaseModel):
    """Information about a system LoRA available to all users."""

    filename: str
    description: str | None = None
    base_model: str | None = None
    source: str | None = None  # "huggingface", "civitai", etc.


class AvailableLorAsResponse(BaseModel):
    """Response with all available LoRAs (system + user)."""

    system_loras: list[SystemLoraInfo]
    user_loras: list[LoRAModelResponse]
