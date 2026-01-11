"""Pydantic models for ComfyUI workflow operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateWorkflowRequest(BaseModel):
    """Request to create a new ComfyUI workflow."""

    name: str = Field(..., description="Workflow name")
    description: str | None = Field(None, description="Workflow description")
    workflow_json: dict[str, Any] = Field(..., description="ComfyUI workflow JSON")
    is_public: bool = Field(default=False, description="Whether workflow is public")
    tags: list[str] = Field(default_factory=list, description="Workflow tags")
    parameter_schema: dict[str, Any] | None = Field(
        None, description="Parameter schema defining workflow parameters"
    )


class UpdateWorkflowRequest(BaseModel):
    """Request to update an existing workflow."""

    name: str | None = None
    description: str | None = None
    workflow_json: dict[str, Any] | None = None
    is_public: bool | None = None
    tags: list[str] | None = None
    parameter_schema: dict[str, Any] | None = None
    status: str | None = Field(
        None, description="Workflow status: 'draft', 'published', or 'archived'"
    )


class WorkflowResponse(BaseModel):
    """Workflow response model."""

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    workflow_json: dict[str, Any]
    is_public: bool
    tags: list[str]
    status: str = Field(
        default="draft", description="Workflow status: 'draft', 'published', or 'archived'"
    )
    published_at: datetime | None = Field(None, description="Timestamp when workflow was published")
    parameter_schema: dict[str, Any] | None = Field(
        None, description="Parameter schema defining workflow parameters"
    )
    created_at: datetime
    updated_at: datetime


class ListWorkflowsResponse(BaseModel):
    """Response from list workflows operation."""

    workflows: list[WorkflowResponse]
    count: int


class RunWorkflowRequest(BaseModel):
    """Request to run a workflow."""

    workflow_id: UUID = Field(..., description="Workflow ID to run")
    input_params: dict[str, Any] | None = Field(
        None, description="Optional input parameters to override workflow values"
    )


class GenerateWorkflowRequest(BaseModel):
    """Request to generate images with parameterized workflow execution."""

    num_images: int | None = Field(1, description="Number of images to generate", ge=1, le=10)
    prompt: str = Field(..., description="Image generation prompt")
    lora_character: str | None = Field(
        None, description="Character name for character-based LoRA selection (e.g., 'Alyx')"
    )
    lora_custom: str | None = Field(None, description="User's custom LoRA name for selection")
    additional_params: dict[str, Any] | None = Field(
        default_factory=dict, description="Any workflow-specific parameters"
    )


class WorkflowRunResponse(BaseModel):
    """Workflow run response model."""

    id: UUID
    workflow_id: UUID | None
    user_id: UUID
    comfyui_request_id: str | None
    status: str
    input_params: dict[str, Any] | None
    output_images: list[str]
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class ListWorkflowRunsResponse(BaseModel):
    """Response from list workflow runs operation."""

    runs: list[WorkflowRunResponse]
    count: int


class CreateLoRAModelRequest(BaseModel):
    """Request to create LoRA model metadata."""

    name: str = Field(..., description="LoRA model name")
    filename: str = Field(..., description="Filename in MinIO")
    minio_path: str = Field(..., description="Full MinIO path")
    file_size: int | None = Field(None, description="File size in bytes")
    description: str | None = Field(None, description="LoRA model description")
    tags: list[str] = Field(default_factory=list, description="LoRA model tags")
    character_name: str | None = Field(
        None, description="Character name for character-based LoRA selection (e.g., 'Alyx')"
    )


class ImportLoRAFromGoogleDriveRequest(BaseModel):
    """Request to import a LoRA model from Google Drive."""

    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    name: str | None = Field(
        None, description="LoRA model name (defaults to Google Drive filename)"
    )
    description: str | None = Field(None, description="LoRA model description")
    tags: list[str] = Field(default_factory=list, description="LoRA model tags")
    character_name: str | None = Field(
        None, description="Character name for character-based LoRA selection (e.g., 'Alyx')"
    )


class LoRAModelResponse(BaseModel):
    """LoRA model response model."""

    id: UUID
    user_id: UUID
    name: str
    filename: str
    minio_path: str
    file_size: int | None
    description: str | None
    tags: list[str]
    character_name: str | None = Field(
        None, description="Character name for character-based LoRA selection"
    )
    created_at: datetime


class ListLoRAModelsResponse(BaseModel):
    """Response from list LoRA models operation."""

    models: list[LoRAModelResponse]
    count: int
