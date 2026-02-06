"""Backwards compatibility module - re-exports from ai/dependencies.

Prefer importing directly from:
    from workflows.automation.n8n_workflow.ai.dependencies import N8nWorkflowDeps
"""

from app.workflows.automation.n8n_workflow.ai.dependencies import N8nWorkflowDeps

__all__ = ["N8nWorkflowDeps"]
