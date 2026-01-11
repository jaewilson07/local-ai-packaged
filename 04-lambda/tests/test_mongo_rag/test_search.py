"""Tests for MongoDB RAG search functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pymongo.errors import OperationFailure

from server.projects.mongo_rag.tools import (
    semantic_search,
    text_search,
    hybrid_search,
    SearchResult
)
from server.projects.mongo_rag.dependencies import AgentDependencies
from tests.conftest import MockRunContext, async_iter


@pytest.mark.asyncio
async def test_semantic_search(mock_agent_dependencies, sample_search_results):
    """Test semantic search returns results."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock aggregation cursor as async iterator
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await semantic_search(ctx, "test query", match_count=5)
    
    # Assert
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].content == sample_search_results[0]["content"]


@pytest.mark.asyncio
async def test_semantic_search_empty_results(mock_agent_dependencies):
    """Test semantic search handles empty results gracefully."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock empty cursor
    mock_cursor = async_iter([])
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await semantic_search(ctx, "nonexistent query", match_count=5)
    
    # Assert
    assert len(results) == 0


@pytest.mark.asyncio
async def test_semantic_search_with_filters(mock_agent_dependencies, sample_search_results):
    """Test semantic search with filters."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    filter_dict = {"metadata.source": "test"}
    
    # Mock aggregation cursor
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await semantic_search(ctx, "test query", match_count=5, filter_dict=filter_dict)
    
    # Assert - verify filter was applied (check aggregation pipeline)
    call_args = mock_collection.aggregate.call_args
    assert call_args is not None
    pipeline = call_args[0][0]
    assert "$vectorSearch" in pipeline[0]
    assert "filter" in pipeline[0]["$vectorSearch"]


@pytest.mark.asyncio
async def test_semantic_search_operation_failure(mock_agent_dependencies):
    """Test semantic search handles OperationFailure gracefully."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock OperationFailure
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(side_effect=OperationFailure("Index not found"))
    
    # Execute
    results = await semantic_search(ctx, "test query", match_count=5)
    
    # Assert - should return empty list on error
    assert len(results) == 0


@pytest.mark.asyncio
async def test_text_search(mock_agent_dependencies, sample_search_results):
    """Test text search returns results."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock aggregation cursor
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await text_search(ctx, "test query", match_count=5)
    
    # Assert
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)


@pytest.mark.asyncio
async def test_text_search_with_filters(mock_agent_dependencies, sample_search_results):
    """Test text search with filters."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    filter_dict = {"metadata.user_id": "user1"}
    
    # Mock aggregation cursor
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await text_search(ctx, "test query", match_count=5, filter_dict=filter_dict)
    
    # Assert - verify filter was applied
    call_args = mock_collection.aggregate.call_args
    assert call_args is not None
    pipeline = call_args[0][0]
    assert "$search" in pipeline[0]
    assert "filter" in pipeline[0]["$search"]


@pytest.mark.asyncio
async def test_hybrid_search(mock_agent_dependencies, sample_search_results):
    """Test hybrid search combines semantic and text results."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock aggregation cursors for both searches
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await hybrid_search(ctx, "test query", match_count=5)
    
    # Assert
    assert len(results) > 0
    # Verify both searches were called
    assert mock_collection.aggregate.call_count >= 2


@pytest.mark.asyncio
async def test_hybrid_search_empty_results(mock_agent_dependencies):
    """Test hybrid search handles empty results gracefully."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock empty cursors
    mock_cursor = async_iter([])
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await hybrid_search(ctx, "nonexistent query", match_count=5)
    
    # Assert
    assert len(results) == 0


@pytest.mark.asyncio
async def test_hybrid_search_with_filters(mock_agent_dependencies, sample_search_results):
    """Test hybrid search with filters."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    filter_dict = {"metadata.source": "test"}
    
    # Mock aggregation cursors
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    mock_collection.aggregate = AsyncMock(return_value=mock_cursor)
    
    # Execute
    results = await hybrid_search(ctx, "test query", match_count=5, filter_dict=filter_dict)
    
    # Assert
    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_search_fallback_on_error(mock_agent_dependencies, sample_search_results):
    """Test hybrid search falls back to semantic search on error."""
    # Setup
    ctx = MockRunContext(mock_agent_dependencies)
    
    # Mock first call to fail, second to succeed
    mock_cursor = async_iter(sample_search_results)
    mock_agent_dependencies.db.__getitem__ = Mock(return_value=AsyncMock())
    mock_collection = mock_agent_dependencies.db["chunks"]
    
    # First call fails, second succeeds (fallback)
    mock_collection.aggregate = AsyncMock(
        side_effect=[Exception("Error"), mock_cursor]
    )
    
    # Execute
    results = await hybrid_search(ctx, "test query", match_count=5)
    
    # Assert - should have results from fallback
    assert len(results) > 0
