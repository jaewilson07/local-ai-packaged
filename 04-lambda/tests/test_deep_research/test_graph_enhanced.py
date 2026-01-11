"""Tests for Phase 6 graph-enhanced reasoning."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from bson import ObjectId

from server.projects.deep_research.tools import query_knowledge
from server.projects.deep_research.models import QueryKnowledgeRequest
from server.projects.deep_research.dependencies import DeepResearchDeps


# ============================================================================
# Graphiti Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_query_knowledge_graphiti_enabled(mock_deep_research_deps, sample_graphiti_result, sample_mongo_chunk):
    """Test Graphiti search integration."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
        use_graphiti=True
    )
    
    # Mock Graphiti search
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]
        
        # Mock MongoDB operations
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test"
            }
        ]))
        
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value=sample_mongo_chunk)
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "title": "Test Document",
            "source": "https://example.com/test"
        })
        mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        assert len(response.results) > 0
        # Graphiti search should be called
        mock_graphiti_search.assert_called_once()


@pytest.mark.asyncio
async def test_query_knowledge_graph_only_mode(mock_deep_research_deps, sample_graphiti_result):
    """Test graph-only search mode."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="graph",
        use_graphiti=True
    )
    
    # Mock Graphiti search
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]
        
        # Mock MongoDB fetch
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value={
            "_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
            "content": sample_graphiti_result.fact,
            "document_id": ObjectId(sample_graphiti_result.metadata["document_id"])
        })
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "source": sample_graphiti_result.metadata["source"]
        })
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        assert len(response.results) > 0
        # Should return early with graph results only
        mock_graphiti_search.assert_called_once()


@pytest.mark.asyncio
async def test_query_knowledge_graph_hybrid_merge(mock_deep_research_deps, sample_graphiti_result, sample_mongo_chunk):
    """Test graph + vector search merging."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
        use_graphiti=True
    )
    
    # Mock Graphiti search
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]
        
        # Mock MongoDB vector search
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test"
            }
        ]))
        
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value=sample_mongo_chunk)
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "title": "Test Document",
            "source": "https://example.com/test"
        })
        mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        # Should have results from both graph and vector search
        assert len(response.results) > 0


@pytest.mark.asyncio
async def test_query_knowledge_graph_deduplication(mock_deep_research_deps, sample_graphiti_result, sample_mongo_chunk):
    """Test result deduplication."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
        use_graphiti=True
    )
    
    # Create graph result with same chunk_id as mongo result
    graph_result = sample_graphiti_result
    graph_result.metadata["chunk_id"] = str(sample_mongo_chunk["_id"])
    
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.return_value = [graph_result]
        
        # Mock MongoDB vector search with same chunk
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test"
            }
        ]))
        
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value=sample_mongo_chunk)
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "title": "Test Document",
            "source": "https://example.com/test"
        })
        mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        # Should deduplicate by chunk_id
        chunk_ids = [r.chunk_id for r in response.results]
        assert len(chunk_ids) == len(set(chunk_ids))  # No duplicates


@pytest.mark.asyncio
async def test_query_knowledge_graph_multi_hop(mock_deep_research_deps, sample_graphiti_result):
    """Test multi-hop reasoning via Graphiti."""
    request = QueryKnowledgeRequest(
        question="What entities are related to deep research?",
        session_id="test-session-123",
        match_count=10,
        search_type="graph",
        use_graphiti=True
    )
    
    # Mock Graphiti to return multiple connected results
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        # Create multiple connected results
        results = [
            sample_graphiti_result,
            type(sample_graphiti_result)(
                fact="Related entity: Research methodology",
                score=0.85,
                similarity=0.85,
                metadata={
                    "chunk_id": "chunk-2",
                    "document_id": "doc-2",
                    "source": "https://example.com/source2"
                },
                content="Related entity: Research methodology"
            )
        ]
        mock_graphiti_search.return_value = results
        
        # Mock MongoDB fetch
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value={
            "_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
            "content": sample_graphiti_result.fact,
            "document_id": ObjectId(sample_graphiti_result.metadata["document_id"])
        })
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "source": sample_graphiti_result.metadata["source"]
        })
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        # Should return multiple results from graph traversal
        assert len(response.results) > 0


# ============================================================================
# Graph Search Tests
# ============================================================================

@pytest.mark.asyncio
async def test_graph_search_entity_relationships(mock_deep_research_deps, sample_graphiti_result):
    """Test entity relationship queries."""
    request = QueryKnowledgeRequest(
        question="What is the relationship between deep research and methodology?",
        session_id="test-session-123",
        match_count=5,
        search_type="graph",
        use_graphiti=True
    )
    
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]
        
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value={
            "_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
            "content": sample_graphiti_result.fact,
            "document_id": ObjectId(sample_graphiti_result.metadata["document_id"])
        })
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "source": sample_graphiti_result.metadata["source"]
        })
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        # Graphiti should handle relationship queries
        mock_graphiti_search.assert_called_once()


@pytest.mark.asyncio
async def test_graph_search_connected_entities(mock_deep_research_deps, sample_graphiti_result):
    """Test connected entity discovery."""
    request = QueryKnowledgeRequest(
        question="What entities are connected to deep research?",
        session_id="test-session-123",
        match_count=10,
        search_type="graph",
        use_graphiti=True
    )
    
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        # Return multiple connected entities
        connected_results = [
            sample_graphiti_result,
            type(sample_graphiti_result)(
                fact="Connected entity 1",
                score=0.8,
                similarity=0.8,
                metadata={"chunk_id": "chunk-2", "document_id": "doc-2", "source": "https://example.com/source2"},
                content="Connected entity 1"
            ),
            type(sample_graphiti_result)(
                fact="Connected entity 2",
                score=0.75,
                similarity=0.75,
                metadata={"chunk_id": "chunk-3", "document_id": "doc-3", "source": "https://example.com/source3"},
                content="Connected entity 2"
            )
        ]
        mock_graphiti_search.return_value = connected_results
        
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value={
            "_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
            "content": sample_graphiti_result.fact,
            "document_id": ObjectId(sample_graphiti_result.metadata["document_id"])
        })
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "source": sample_graphiti_result.metadata["source"]
        })
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        assert response.success is True
        # Should discover connected entities via graph traversal
        assert len(response.results) > 0


@pytest.mark.asyncio
async def test_graph_search_fallback(mock_deep_research_deps, sample_mongo_chunk):
    """Test fallback to standard search if Graphiti fails."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
        use_graphiti=True
    )
    
    # Mock Graphiti to fail
    with patch("server.projects.deep_research.tools.graphiti_search") as mock_graphiti_search:
        mock_graphiti_search.side_effect = Exception("Graphiti unavailable")
        
        # Mock MongoDB vector search as fallback
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test"
            }
        ]))
        
        mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(return_value={
            "title": "Test Document",
            "source": "https://example.com/test"
        })
        
        response = await query_knowledge(mock_deep_research_deps, request)
        
        # Should fall back to standard search
        assert response.success is True
        assert len(response.results) > 0
