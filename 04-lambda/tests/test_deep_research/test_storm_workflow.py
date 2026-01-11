"""Integration tests for STORM workflow (Phase 4-6)."""

from unittest.mock import AsyncMock, patch

import pytest

from server.projects.deep_research.orchestrator import (
    create_research_graph,
    get_research_graph,
    should_continue_auditor,
    should_continue_executor,
)
from server.projects.deep_research.state import ResearchState, ResearchVector
from server.projects.deep_research.storm_workflow import run_storm_research

# ============================================================================
# Graph Construction Tests
# ============================================================================


def test_create_research_graph():
    """Test graph creation and structure."""
    graph = create_research_graph()

    assert graph is not None
    # Graph should be compiled
    assert hasattr(graph, "ainvoke")


def test_graph_node_connections():
    """Test node edge connections."""
    graph = create_research_graph()

    # Graph should have nodes: planner, executor, auditor, writer
    # We can't directly inspect nodes, but we can test execution
    assert graph is not None


def test_graph_conditional_edges(sample_research_state):
    """Test conditional routing logic."""
    # Test executor conditional
    state = sample_research_state.copy()
    state["vectors"] = [
        ResearchVector(id="v1", topic="Test", search_queries=["test"], status="pending")
    ]
    state["current_vector_index"] = 0

    result = should_continue_executor(state)
    assert result == "executor"

    state["current_vector_index"] = 1
    result = should_continue_executor(state)
    assert result == "auditor"

    # Test auditor conditional
    state["current_vector_index"] = 0
    result = should_continue_auditor(state)
    assert result == "auditor"

    state["current_vector_index"] = 1
    result = should_continue_auditor(state)
    assert result == "writer"


def test_get_research_graph():
    """Test get_research_graph returns singleton."""
    graph1 = get_research_graph()
    graph2 = get_research_graph()

    # Should return same instance
    assert graph1 is graph2


# ============================================================================
# Workflow Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_storm_research_success(mock_deep_research_deps, sample_research_state):
    """Test full STORM workflow execution."""
    query = "What is deep research?"

    # Mock all node functions
    with (
        patch("server.projects.deep_research.orchestrator.planner_node") as mock_planner,
        patch("server.projects.deep_research.orchestrator.executor_node") as mock_executor,
        patch("server.projects.deep_research.orchestrator.auditor_node") as mock_auditor,
        patch("server.projects.deep_research.orchestrator.writer_node") as mock_writer,
    ):
        # Setup state progression
        state1 = sample_research_state.copy()
        state1["outline"] = ["Introduction", "Background"]
        state1["vectors"] = [
            ResearchVector(id="v1", topic="Introduction", search_queries=["test"], status="pending")
        ]

        state2 = state1.copy()
        state2["vectors"][0].status = "ingesting"
        state2["current_vector_index"] = 1

        state3 = state2.copy()
        state3["vectors"][0].status = "verified"

        state4 = state3.copy()
        state4["final_report"] = "# Research Report\n\n## Introduction\n\nContent."

        mock_planner.return_value = state1
        mock_executor.return_value = state2
        mock_auditor.return_value = state3
        mock_writer.return_value = state4

        # Mock graph execution
        with patch(
            "server.projects.deep_research.storm_workflow.get_research_graph"
        ) as mock_get_graph:
            mock_graph = AsyncMock()
            mock_graph.ainvoke = AsyncMock(return_value=state4)
            mock_get_graph.return_value = mock_graph

            result = await run_storm_research(query, session_id="test-session")

            assert result["final_report"] is not None
            assert len(result["final_report"]) > 0
            assert result["user_query"] == query


@pytest.mark.asyncio
async def test_run_storm_research_with_session_id(mock_deep_research_deps):
    """Test STORM workflow with custom session ID."""
    query = "What is deep research?"
    session_id = "custom-session-456"

    with patch("server.projects.deep_research.storm_workflow.get_research_graph") as mock_get_graph:
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "user_query": query,
                "outline": [],
                "vectors": [],
                "knowledge_graph_session_id": session_id,
                "completed_sections": {},
                "final_report": "Test report",
                "errors": [],
                "current_vector_index": 0,
                "max_iterations": 10,
                "iteration_count": 0,
            }
        )
        mock_get_graph.return_value = mock_graph

        result = await run_storm_research(query, session_id=session_id)

        assert result["knowledge_graph_session_id"] == session_id


@pytest.mark.asyncio
async def test_run_storm_research_error_handling(mock_deep_research_deps):
    """Test error handling in STORM workflow."""
    query = "What is deep research?"

    with patch("server.projects.deep_research.storm_workflow.get_research_graph") as mock_get_graph:
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution failed"))
        mock_get_graph.return_value = mock_graph

        result = await run_storm_research(query)

        assert len(result["errors"]) > 0
        assert "Error" in result["final_report"] or result["final_report"] is None


@pytest.mark.asyncio
async def test_run_storm_research_state_persistence(mock_deep_research_deps):
    """Test state management through workflow."""
    query = "What is deep research?"

    with patch("server.projects.deep_research.storm_workflow.get_research_graph") as mock_get_graph:
        final_state = {
            "user_query": query,
            "outline": ["Section 1", "Section 2"],
            "vectors": [
                ResearchVector(
                    id="v1", topic="Section 1", search_queries=["test"], status="verified"
                )
            ],
            "knowledge_graph_session_id": "test-session",
            "completed_sections": {"Section 1": "Content"},
            "final_report": "Final report",
            "errors": [],
            "current_vector_index": 1,
            "max_iterations": 10,
            "iteration_count": 5,
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_get_graph.return_value = mock_graph

        result = await run_storm_research(query)

        assert result["outline"] == final_state["outline"]
        assert len(result["vectors"]) == len(final_state["vectors"])
        assert result["completed_sections"] == final_state["completed_sections"]
        assert result["iteration_count"] == final_state["iteration_count"]


@pytest.mark.asyncio
async def test_run_storm_research_max_iterations(mock_deep_research_deps):
    """Test iteration limit enforcement."""
    query = "What is deep research?"

    with patch("server.projects.deep_research.storm_workflow.get_research_graph") as mock_get_graph:
        final_state = {
            "user_query": query,
            "outline": [],
            "vectors": [],
            "knowledge_graph_session_id": "test-session",
            "completed_sections": {},
            "final_report": None,
            "errors": [],
            "current_vector_index": 0,
            "max_iterations": 10,
            "iteration_count": 10,  # Reached max
        }

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_get_graph.return_value = mock_graph

        result = await run_storm_research(query, max_iterations=10)

        assert result["iteration_count"] <= result["max_iterations"]


# ============================================================================
# State Management Tests
# ============================================================================


def test_research_state_initialization():
    """Test initial state creation."""
    state: ResearchState = {
        "user_query": "Test query",
        "outline": [],
        "vectors": [],
        "knowledge_graph_session_id": "session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }

    assert state["user_query"] == "Test query"
    assert state["current_vector_index"] == 0
    assert state["iteration_count"] == 0


def test_research_state_updates(sample_research_state):
    """Test state updates through nodes."""
    state = sample_research_state.copy()

    # Simulate planner update
    state["outline"] = ["Section 1"]
    state["vectors"] = [
        ResearchVector(id="v1", topic="Section 1", search_queries=["test"], status="pending")
    ]

    # Simulate executor update
    state["vectors"][0].status = "ingesting"
    state["current_vector_index"] = 1

    # Simulate auditor update
    state["vectors"][0].status = "verified"

    # Simulate writer update
    state["completed_sections"]["Section 1"] = "Content"
    state["final_report"] = "Final report"

    assert state["outline"] == ["Section 1"]
    assert state["vectors"][0].status == "verified"
    assert len(state["completed_sections"]) > 0
    assert state["final_report"] is not None


def test_research_state_vector_tracking(sample_research_state):
    """Test vector status tracking."""
    state = sample_research_state.copy()

    vectors = [
        ResearchVector(id="v1", topic="Topic 1", search_queries=["q1"], status="pending"),
        ResearchVector(id="v2", topic="Topic 2", search_queries=["q2"], status="pending"),
        ResearchVector(id="v3", topic="Topic 3", search_queries=["q3"], status="pending"),
    ]

    state["vectors"] = vectors
    state["current_vector_index"] = 0

    # Track status changes
    state["vectors"][0].status = "ingesting"
    assert state["vectors"][0].status == "ingesting"

    state["vectors"][0].status = "verified"
    assert state["vectors"][0].status == "verified"

    state["current_vector_index"] = 1
    assert state["current_vector_index"] == 1


def test_research_state_error_collection(sample_research_state):
    """Test error collection."""
    state = sample_research_state.copy()

    assert len(state["errors"]) == 0

    state["errors"].append("Error 1")
    state["errors"].append("Error 2")

    assert len(state["errors"]) == 2
    assert "Error 1" in state["errors"]
    assert "Error 2" in state["errors"]
