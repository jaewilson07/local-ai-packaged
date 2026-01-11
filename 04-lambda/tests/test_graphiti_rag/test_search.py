"""Tests for Graphiti RAG knowledge graph search."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from tests.conftest import MockRunContext

from server.projects.graphiti_rag.tools import search_graphiti_knowledge_graph
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.config import config as graphiti_config


@pytest.mark.asyncio
async def test_search_graphiti(mock_graphiti_rag_deps, sample_graph_fact):
    """Test Graphiti knowledge graph search."""
    from types import SimpleNamespace
    
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    
    # Mock Graphiti search with proper result object
    mock_graph_result = SimpleNamespace()
    mock_graph_result.fact = sample_graph_fact["content"]
    mock_graph_result.score = float(sample_graph_fact["similarity"])
    mock_graph_result.similarity = float(sample_graph_fact["similarity"])
    mock_graph_result.metadata = sample_graph_fact["metadata"]
    mock_graph_result.metadata["chunk_id"] = sample_graph_fact["chunk_id"]
    mock_graphiti_rag_deps.graphiti.search = AsyncMock(return_value=[mock_graph_result])
    
    # Execute
    result = await search_graphiti_knowledge_graph(ctx, "Python programming", match_count=10)
    
    # Assert
    assert result["success"] is True
    assert result["count"] > 0
    assert len(result["results"]) > 0
    assert result["results"][0]["fact"] == sample_graph_fact["content"]


@pytest.mark.asyncio
async def test_search_with_match_count(mock_graphiti_rag_deps):
    """Test search with match count limit."""
    from types import SimpleNamespace
    
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    
    # Mock search to return limited results based on limit parameter
    async def mock_search(query, limit=10):
        mock_results = []
        for i in range(limit):  # Return only up to limit
            r = SimpleNamespace()
            r.fact = f"Fact {i}"
            r.score = float(0.9 - (i * 0.01))
            r.similarity = float(0.9 - (i * 0.01))
            r.metadata = {"chunk_id": f"fact_{i}"}
            mock_results.append(r)
        return mock_results
    
    mock_graphiti_rag_deps.graphiti.search = AsyncMock(side_effect=mock_search)
    
    # Execute with limit
    result = await search_graphiti_knowledge_graph(ctx, "test query", match_count=10)
    
    # Assert
    assert result["success"] is True
    assert result["count"] == 10
    assert len(result["results"]) == 10


@pytest.mark.asyncio
async def test_search_empty_results(mock_graphiti_rag_deps):
    """Test search with no results."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    
    # Mock empty results
    mock_graphiti_rag_deps.graphiti.search = AsyncMock(return_value=[])
    
    # Execute
    result = await search_graphiti_knowledge_graph(ctx, "nonexistent query", match_count=10)
    
    # Assert
    assert result["success"] is True
    assert result["count"] == 0
    assert len(result["results"]) == 0


@pytest.mark.asyncio
async def test_search_feature_flag(mock_graphiti_rag_deps):
    """Test search checks USE_GRAPHITI flag."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    
    # Mock Graphiti not initialized
    mock_graphiti_rag_deps.graphiti = None
    
    # Execute and expect error
    with pytest.raises(ValueError, match="Graphiti client is not initialized"):
        await search_graphiti_knowledge_graph(ctx, "test query", match_count=10)


@pytest.mark.asyncio
async def test_search_error_handling(mock_graphiti_rag_deps):
    """Test search error handling."""
    # Setup
    ctx = MockRunContext(mock_graphiti_rag_deps)
    
    # Mock Graphiti search error - graphiti_search catches and returns []
    # so search_graphiti_knowledge_graph returns success=True with empty results
    mock_graphiti_rag_deps.graphiti.search = AsyncMock(side_effect=Exception("Graphiti error"))
    
    # Execute
    result = await search_graphiti_knowledge_graph(ctx, "test query", match_count=10)
    
    # Assert - graphiti_search catches exception and returns [], so we get success=True with empty results
    assert result["success"] is True
    assert result["count"] == 0
    assert len(result["results"]) == 0