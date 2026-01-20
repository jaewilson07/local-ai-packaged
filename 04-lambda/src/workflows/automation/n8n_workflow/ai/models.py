"""Backwards compatibility module - re-exports from schemas.

All models have moved to the schemas/ directory. This file maintains
backwards compatibility with imports that use the old path.

Prefer importing directly from schemas:
    from workflows.automation.n8n_workflow.schemas import CreateWorkflowRequest
"""

from workflows.automation.n8n_workflow.schemas import (
    ActivateWorkflowRequest,
    CreateWorkflowRequest,
    DeleteWorkflowRequest,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ListWorkflowsResponse,
    UpdateWorkflowRequest,
    WorkflowConnection,
    WorkflowNode,
    WorkflowResponse,
)

__all__ = [
    "ActivateWorkflowRequest",
    "CreateWorkflowRequest",
    "DeleteWorkflowRequest",
    "ExecuteWorkflowRequest",
    "ExecuteWorkflowResponse",
    "ListWorkflowsResponse",
    "UpdateWorkflowRequest",
    "WorkflowConnection",
    "WorkflowNode",
    "WorkflowResponse",
]
