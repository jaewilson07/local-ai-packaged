"""N8n Workflow Automation module.

This module provides N8n workflow automation capabilities organized by:
- schemas/: Request/Response models
- ai/: Agent definitions and dependencies
- workflow.py: High-level orchestration functions
- router.py: FastAPI endpoints
- tools.py: Core capability functions
"""

from workflows.automation.n8n_workflow.ai import N8nDeps, N8nState, n8n_agent
from workflows.automation.n8n_workflow.schemas import (
    CreateWorkflowRequest,
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    WorkflowResponse,
)
from workflows.automation.n8n_workflow.workflow import (
    create_workflow_automation,
    execute_workflow_automation,
)

__all__ = [
    # Schemas
    "CreateWorkflowRequest",
    "ExecuteWorkflowRequest",
    "WorkflowResponse",
    "ExecuteWorkflowResponse",
    # AI Components
    "n8n_agent",
    "N8nState",
    "N8nDeps",
    # Workflows
    "create_workflow_automation",
    "execute_workflow_automation",
]
