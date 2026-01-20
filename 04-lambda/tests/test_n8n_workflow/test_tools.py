"""Tests for N8N Workflow tools."""

from unittest.mock import AsyncMock, Mock

import pytest
from server.projects.n8n_workflow.dependencies import N8nWorkflowDeps
from server.projects.n8n_workflow.tools import (
    create_workflow,
    execute_workflow,
    list_workflows,
)


@pytest.fixture
def mock_n8n_deps():
    """Create mock N8nWorkflowDeps."""
    deps = N8nWorkflowDeps.from_settings()
    deps.http_client = AsyncMock()
    return deps


@pytest.fixture
def mock_n8n_ctx(mock_n8n_deps):
    """Create mock RunContext for N8N tools."""
    from tests.conftest import MockRunContext

    return MockRunContext(mock_n8n_deps)


@pytest.mark.asyncio
async def test_create_workflow_success(mock_n8n_ctx):
    """Test creating a workflow successfully."""
    # Setup
    mock_response = Mock()
    mock_response.json = Mock(
        return_value={"id": "workflow_123", "name": "Test Workflow", "active": False}
    )
    mock_response.raise_for_status = Mock()
    mock_n8n_ctx.deps.http_client.post = AsyncMock(return_value=mock_response)

    # Execute
    result = await create_workflow(
        mock_n8n_ctx, name="Test Workflow", nodes=[], connections={}, active=False
    )

    # Assert
    assert isinstance(result, str)
    assert "workflow" in result.lower()
    assert "workflow_123" in result
    mock_n8n_ctx.deps.http_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_list_workflows_success(mock_n8n_ctx):
    """Test listing workflows successfully."""
    # Setup
    mock_workflows = [
        {"id": "workflow_1", "name": "Workflow 1", "active": True},
        {"id": "workflow_2", "name": "Workflow 2", "active": False},
    ]
    mock_response = AsyncMock()
    mock_response.json.return_value = {"workflows": mock_workflows}
    mock_response.raise_for_status = Mock()
    mock_n8n_ctx.deps.http_client.get = AsyncMock(return_value=mock_response)

    # Execute
    result = await list_workflows(mock_n8n_ctx, active_only=False)

    # Assert
    assert isinstance(result, str)
    assert "workflow" in result.lower()
    mock_n8n_ctx.deps.http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_execute_workflow_success(mock_n8n_ctx):
    """Test executing a workflow successfully."""
    # Setup
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "execution_id": "exec_123",
        "status": "success",
        "data": {"result": "test"},
    }
    mock_response.raise_for_status = Mock()
    mock_n8n_ctx.deps.http_client.post = AsyncMock(return_value=mock_response)

    # Execute
    result = await execute_workflow(
        mock_n8n_ctx, workflow_id="workflow_123", input_data={"test": "data"}
    )

    # Assert
    assert isinstance(result, str)
    assert "execution" in result.lower() or "workflow" in result.lower()
    mock_n8n_ctx.deps.http_client.post.assert_called_once()
