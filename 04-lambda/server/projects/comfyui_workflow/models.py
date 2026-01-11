"""Pydantic models for ComfyUI workflow operations."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class CreateWorkflowRequest(BaseModel):
    """Request to create a new ComfyUI workflow."""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    workflow_json: Dict[str, Any] = Field(..., description="ComfyUI workflow JSON")
    is_public: bool = Field(default=False, description="Whether workflow is public")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")


class UpdateWorkflowRequest(BaseModel):
    """Request to update an existing workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    workflow_json: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class WorkflowResponse(BaseModel):
    """Workflow response model."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    workflow_json: Dict[str, Any]
    is_public: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class ListWorkflowsResponse(BaseModel):
    """Response from list workflows operation."""
    workflows: List[WorkflowResponse]
    count: int


class RunWorkflowRequest(BaseModel):
    """Request to run a workflow."""
    workflow_id: UUID = Field(..., description="Workflow ID to run")
    input_params: Optional[Dict[str, Any]] = Field(None, description="Optional input parameters to override workflow values")


class WorkflowRunResponse(BaseModel):
    """Workflow run response model."""
    id: UUID
    workflow_id: Optional[UUID]
    user_id: UUID
    comfyui_request_id: Optional[str]
    status: str
    input_params: Optional[Dict[str, Any]]
    output_images: List[str]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


class ListWorkflowRunsResponse(BaseModel):
    """Response from list workflow runs operation."""
    runs: List[WorkflowRunResponse]
    count: int


class CreateLoRAModelRequest(BaseModel):
    """Request to create LoRA model metadata."""
    name: str = Field(..., description="LoRA model name")
    filename: str = Field(..., description="Filename in MinIO")
    minio_path: str = Field(..., description="Full MinIO path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    description: Optional[str] = Field(None, description="LoRA model description")
    tags: List[str] = Field(default_factory=list, description="LoRA model tags")


class ImportLoRAFromGoogleDriveRequest(BaseModel):
    """Request to import a LoRA model from Google Drive."""
    google_drive_file_id: str = Field(..., description="Google Drive file ID")
    name: Optional[str] = Field(None, description="LoRA model name (defaults to Google Drive filename)")
    description: Optional[str] = Field(None, description="LoRA model description")
    tags: List[str] = Field(default_factory=list, description="LoRA model tags")


class LoRAModelResponse(BaseModel):
    """LoRA model response model."""
    id: UUID
    user_id: UUID
    name: str
    filename: str
    minio_path: str
    file_size: Optional[int]
    description: Optional[str]
    tags: List[str]
    created_at: datetime


class ListLoRAModelsResponse(BaseModel):
    """Response from list LoRA models operation."""
    models: List[LoRAModelResponse]
    count: int
