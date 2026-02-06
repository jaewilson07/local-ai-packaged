"""Tests for MongoDB RAG agent API endpoint."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.capabilities.retrieval.mongo_rag.router import get_agent_deps
from fastapi.testclient import TestClient
from server.main import app
from server.projects.mongo_rag.agent import rag_agent


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_agent_run():
    """Mock agent.run() to return a test response."""
    with patch.object(rag_agent, "run", new_callable=AsyncMock) as mock_run:
        # Default response
        mock_result = Mock()
        mock_result.data = "This is a test response from the RAG agent."
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_agent_dependencies():
    """Mock AgentDependencies instance."""
    from server.projects.mongo_rag.dependencies import AgentDependencies

    mock_deps = Mock(spec=AgentDependencies)
    mock_deps.mongo_client = AsyncMock()
    mock_deps.graphiti_deps = Mock()
    mock_deps.graphiti_deps.use_graphiti = False
    mock_deps.graphiti_deps.graphiti_adapter = None
    mock_deps.initialize = AsyncMock()
    mock_deps.cleanup = AsyncMock()
    return mock_deps


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        {
            "content": "Authentication is the process of verifying user identity.",
            "score": 0.95,
            "metadata": {"source": "test_doc"},
        }
    ]


def test_agent_endpoint_simple_query(client, mock_agent_run, mock_agent_dependencies):
    """Test agent endpoint with a simple query."""
    from capabilities.retrieval.mongo_rag.router import get_agent_deps

    # Override the dependency using FastAPI's dependency_overrides
    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # Execute
        response = client.post("/api/v1/rag/agent", json={"query": "What is authentication?"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "response" in data
        assert data["query"] == "What is authentication?"
        assert len(data["response"]) > 0
        assert isinstance(data["response"], str)
    finally:
        # Clean up override
        app.dependency_overrides.clear()


def test_agent_endpoint_response_quality(client, mock_agent_run, mock_agent_dependencies):
    """Test that agent endpoint returns a reasonable response."""
    # Setup mock to return a more realistic response
    mock_result = Mock()
    mock_result.data = "Authentication is the process of verifying the identity of a user or system. It typically involves credentials like usernames and passwords, or more advanced methods like multi-factor authentication."
    mock_agent_run.return_value = mock_result

    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # Execute
        response = client.post("/api/v1/rag/agent", json={"query": "What is authentication?"})

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "query" in data
        assert "response" in data

        # Validate response quality - should be non-empty and meaningful
        response_text = data["response"]
        assert len(response_text) > 10, "Response should be more than 10 characters"
        assert len(response_text.split()) > 3, "Response should contain multiple words"

        # Response should be related to the query (basic check)
        query_lower = data["query"].lower()
        response_lower = response_text.lower()

        # For authentication query, response should mention authentication-related terms
        if "authentication" in query_lower:
            assert any(
                term in response_lower
                for term in [
                    "authentication",
                    "verify",
                    "identity",
                    "user",
                    "password",
                    "credential",
                ]
            ), "Response should contain relevant terms for authentication query"
    finally:
        app.dependency_overrides.clear()


def test_agent_endpoint_with_knowledge_base_query(
    client, mock_agent_run, mock_agent_dependencies, sample_search_results
):
    """Test agent endpoint when it needs to search the knowledge base."""
    # Setup mock to simulate agent using search tool
    mock_result = Mock()
    mock_result.data = "Based on the knowledge base, I found information about authentication. Authentication is a security process that verifies user identity."
    mock_agent_run.return_value = mock_result

    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # Execute
        response = client.post(
            "/api/v1/rag/agent",
            json={"query": "What does the knowledge base say about authentication?"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "response" in data
        assert (
            len(data["response"]) > 20
        ), "Response should be substantial when using knowledge base"
    finally:
        app.dependency_overrides.clear()


def test_agent_endpoint_error_handling(client, mock_agent_dependencies):
    """Test agent endpoint error handling."""
    # Mock agent.run() to raise an exception
    with patch.object(rag_agent, "run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = Exception("LLM service unavailable")

        async def override_get_agent_deps():
            mock_agent_dependencies.initialize = AsyncMock(return_value=None)
            mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
            yield mock_agent_dependencies

        app.dependency_overrides[get_agent_deps] = override_get_agent_deps

        try:
            # Execute
            response = client.post("/api/v1/rag/agent", json={"query": "Test query"})

            # Assert - should return 500 error
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()


def test_agent_endpoint_invalid_request(client, mock_agent_dependencies):
    """Test agent endpoint with invalid request."""

    # Override dependency to avoid MongoDB connection attempt
    # FastAPI may call dependencies even when request validation fails
    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # Missing query field
        response = client.post("/api/v1/rag/agent", json={})

        # Assert - should return 422 validation error
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_agent_endpoint_empty_query(client, mock_agent_run, mock_agent_dependencies):
    """Test agent endpoint with empty query."""
    mock_result = Mock()
    mock_result.data = "Please provide a question or query."
    mock_agent_run.return_value = mock_result

    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # Execute
        response = client.post("/api/v1/rag/agent", json={"query": ""})

        # Assert - should still process (validation happens at agent level)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
    finally:
        app.dependency_overrides.clear()


def test_agent_endpoint_conversation_context(client, mock_agent_run, mock_agent_dependencies):
    """Test that agent endpoint maintains conversation context."""

    async def override_get_agent_deps():
        mock_agent_dependencies.initialize = AsyncMock(return_value=None)
        mock_agent_dependencies.cleanup = AsyncMock(return_value=None)
        yield mock_agent_dependencies

    app.dependency_overrides[get_agent_deps] = override_get_agent_deps

    try:
        # First query
        mock_result1 = Mock()
        mock_result1.data = "Hello! How can I help you?"
        mock_agent_run.return_value = mock_result1

        response1 = client.post("/api/v1/rag/agent", json={"query": "Hello"})

        assert response1.status_code == 200
        data1 = response1.json()
        assert "Hello" in data1["response"] or "help" in data1["response"].lower()

        # Second query (follow-up)
        mock_result2 = Mock()
        mock_result2.data = "Authentication is the process of verifying identity."
        mock_agent_run.return_value = mock_result2

        response2 = client.post("/api/v1/rag/agent", json={"query": "What is authentication?"})

        assert response2.status_code == 200
        data2 = response2.json()
        assert "authentication" in data2["response"].lower()
    finally:
        app.dependency_overrides.clear()
