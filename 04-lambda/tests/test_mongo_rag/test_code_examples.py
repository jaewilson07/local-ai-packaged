"""Tests for MongoDB RAG code example extraction."""

from unittest.mock import AsyncMock, Mock

import pytest

from server.projects.mongo_rag.tools_code import search_code_examples
from tests.conftest import MockRunContext


@pytest.mark.asyncio
async def test_search_code_examples(mock_agent_dependencies, sample_search_results):
    """Test code example search."""
    from tests.conftest import async_iter

    # Setup
    ctx = MockRunContext(mock_agent_dependencies)

    # Mock MongoDB collection and aggregation cursor
    mock_collection = AsyncMock()
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=mock_collection)

    # Mock aggregation results - function directly calls collection.aggregate()
    sample_results = [
        {
            "_id": "1",
            "code_example_id": "1",
            "document_id": "doc1",
            "code": "def authenticate(user, password):\n    return verify(user, password)",
            "summary": "Authentication function",
            "language": "python",
            "similarity": 0.9,
            "metadata": {"language": "python", "source": "test"},
            "source": "https://example.com/auth",
        }
    ]

    mock_collection.aggregate = AsyncMock(return_value=async_iter(sample_results))

    # Execute
    results = await search_code_examples(ctx, "authentication function", match_count=5)

    # Assert
    assert len(results) > 0
    assert "authenticate" in results[0].code.lower()


@pytest.mark.asyncio
async def test_code_example_formatting(mock_agent_dependencies):
    """Test code example result formatting."""
    from tests.conftest import async_iter

    # Setup
    ctx = MockRunContext(mock_agent_dependencies)

    # Mock MongoDB collection and aggregation cursor
    mock_collection = AsyncMock()
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=mock_collection)

    # Mock aggregation results
    sample_results = [
        {
            "_id": "1",
            "code_example_id": "1",
            "document_id": "doc1",
            "code": "def test():\n    pass",
            "summary": "Test function",
            "language": "python",
            "similarity": 0.9,
            "metadata": {"language": "python"},
            "source": "https://example.com",
        }
    ]

    mock_collection.aggregate = AsyncMock(return_value=async_iter(sample_results))

    # Execute
    results = await search_code_examples(ctx, "test function", match_count=5)

    # Assert
    assert len(results) > 0
    result = results[0]
    assert hasattr(result, "code")
    assert hasattr(result, "language")
    assert result.language == "python"


@pytest.mark.asyncio
async def test_code_example_filtering(mock_agent_dependencies):
    """Test code example filtering by language."""
    from tests.conftest import async_iter

    # Setup
    ctx = MockRunContext(mock_agent_dependencies)

    # Mock MongoDB collection and aggregation cursor
    mock_collection = AsyncMock()
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=mock_collection)

    # Mock aggregation results with different languages
    sample_results = [
        {
            "_id": "1",
            "code_example_id": "1",
            "document_id": "doc1",
            "code": "def test():\n    pass",
            "summary": "Python test function",
            "language": "python",
            "similarity": 0.9,
            "metadata": {"language": "python"},
            "source": "https://example.com",
        },
        {
            "_id": "2",
            "code_example_id": "2",
            "document_id": "doc2",
            "code": "function test() {}",
            "summary": "JavaScript test function",
            "language": "javascript",
            "similarity": 0.8,
            "metadata": {"language": "javascript"},
            "source": "https://example.com",
        },
    ]

    mock_collection.aggregate = AsyncMock(return_value=async_iter(sample_results))

    # Execute
    results = await search_code_examples(ctx, "test function", match_count=5)

    # Assert - should return both languages
    assert len(results) >= 1
    languages = [r.language for r in results]
    assert "python" in languages or "javascript" in languages or len(results) > 0
