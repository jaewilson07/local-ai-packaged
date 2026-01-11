"""Pydantic models for N8n workflow operations."""

from typing import Any

from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    """N8n workflow node definition."""

    name: str
    type: str
    typeVersion: float = 1.0
    position: list[float] = Field(default=[250, 300])
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowConnection(BaseModel):
    """N8n workflow connection definition."""

    source: str
    target: str
    sourceOutput: str = "main"
    targetInput: str = "main"


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow."""

    name: str = Field(..., description="Workflow name")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    connections: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict, description="Workflow connections"
    )
    active: bool = Field(default=False, description="Whether to activate the workflow")
    settings: dict[str, Any] = Field(default_factory=dict, description="Workflow settings")


class UpdateWorkflowRequest(BaseModel):
    """Request to update an existing workflow."""

    workflow_id: str = Field(..., description="Workflow ID")
    name: str | None = None
    nodes: list[WorkflowNode] | None = None
    connections: dict[str, list[dict[str, Any]]] | None = None
    active: bool | None = None
    settings: dict[str, Any] | None = None


class WorkflowResponse(BaseModel):
    """Response from workflow operations."""

    success: bool
    workflow_id: str | None = None
    message: str
    data: dict[str, Any] | None = None


class ListWorkflowsResponse(BaseModel):
    """Response from list workflows operation."""

    success: bool
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    workflow_id: str = Field(..., description="Workflow ID")
    input_data: dict[str, Any] | None = Field(
        default_factory=dict, description="Input data for workflow execution"
    )


class ExecuteWorkflowResponse(BaseModel):
    """Response from workflow execution."""

    success: bool
    execution_id: str | None = None
    message: str
    data: dict[str, Any] | None = None


class ActivateWorkflowRequest(BaseModel):
    """Request to activate or deactivate a workflow."""

    workflow_id: str = Field(..., description="Workflow ID")
    active: bool = Field(..., description="Whether to activate (true) or deactivate (false)")


class DeleteWorkflowRequest(BaseModel):
    """Request to delete a workflow."""

    workflow_id: str = Field(..., description="Workflow ID to delete")
