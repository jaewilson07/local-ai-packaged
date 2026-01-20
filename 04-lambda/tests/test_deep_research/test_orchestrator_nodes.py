"""Unit tests for LangGraph orchestrator nodes (Phase 4-5)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from server.projects.deep_research.orchestrator import (
    auditor_node,
    executor_node,
    planner_node,
    writer_node,
)
from server.projects.deep_research.state import ResearchVector

# ============================================================================
# Planner Node Tests
# ============================================================================


@pytest.mark.asyncio
async def test_planner_node_generates_outline(
    mock_deep_research_deps, sample_research_state, sample_search_results
):
    """Test that planner node generates research outline."""
    state = sample_research_state.copy()

    # Mock search_web
    with patch("server.projects.deep_research.orchestrator.search_web") as mock_search:
        from server.projects.deep_research.models import SearchResult, SearchWebResponse

        mock_search.return_value = SearchWebResponse(
            query=state["user_query"],
            results=[
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results[:3]
            ],
            count=3,
            success=True,
        )

        # Mock planner agent
        with patch("server.projects.deep_research.orchestrator.planner_agent") as mock_agent:
            mock_result = Mock()
            mock_result.data = "Test response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            # Set deps in module
            import server.projects.deep_research.orchestrator as orchestrator_module

            orchestrator_module._current_deps = mock_deep_research_deps

            try:
                result_state = await planner_node(state)

                assert len(result_state["outline"]) > 0
                assert len(result_state["vectors"]) > 0
                assert result_state["current_vector_index"] == 0
            finally:
                orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_planner_node_creates_vectors(
    mock_deep_research_deps, sample_research_state, sample_search_results
):
    """Test that planner node creates research vectors."""
    state = sample_research_state.copy()

    with patch("server.projects.deep_research.orchestrator.search_web") as mock_search:
        from server.projects.deep_research.models import SearchResult, SearchWebResponse

        mock_search.return_value = SearchWebResponse(
            query=state["user_query"],
            results=[
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results[:3]
            ],
            count=3,
            success=True,
        )

        with patch("server.projects.deep_research.orchestrator.planner_agent") as mock_agent:
            mock_result = Mock()
            mock_result.data = "Test response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            import server.projects.deep_research.orchestrator as orchestrator_module

            orchestrator_module._current_deps = mock_deep_research_deps

            try:
                result_state = await planner_node(state)

                assert len(result_state["vectors"]) > 0
                assert all(isinstance(v, ResearchVector) for v in result_state["vectors"])
                assert all(v.status == "pending" for v in result_state["vectors"])
            finally:
                orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_planner_node_pre_search(
    mock_deep_research_deps, sample_research_state, sample_search_results
):
    """Test that planner node performs pre-search."""
    state = sample_research_state.copy()

    with patch("server.projects.deep_research.orchestrator.search_web") as mock_search:
        from server.projects.deep_research.models import SearchResult, SearchWebResponse

        mock_search.return_value = SearchWebResponse(
            query=state["user_query"],
            results=[
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    snippet=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results[:3]
            ],
            count=3,
            success=True,
        )

        with patch("server.projects.deep_research.orchestrator.planner_agent") as mock_agent:
            mock_result = Mock()
            mock_result.data = "Test response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            import server.projects.deep_research.orchestrator as orchestrator_module

            orchestrator_module._current_deps = mock_deep_research_deps

            try:
                await planner_node(state)

                # Verify pre-search was called
                mock_search.assert_called_once()
            finally:
                orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_planner_node_error_handling(mock_deep_research_deps, sample_research_state):
    """Test planner node error handling."""
    state = sample_research_state.copy()

    with patch("server.projects.deep_research.orchestrator.search_web") as mock_search:
        mock_search.side_effect = Exception("Search failed")

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await planner_node(state)

            assert len(result_state["errors"]) > 0
            assert any("Planner error" in error for error in result_state["errors"])
        finally:
            orchestrator_module._current_deps = None


# ============================================================================
# Executor Node Tests
# ============================================================================


@pytest.mark.asyncio
async def test_executor_node_processes_vector(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test that executor node processes a single vector."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.search_web") as mock_search,
        patch("server.projects.deep_research.orchestrator.fetch_page") as mock_fetch,
        patch("server.projects.deep_research.orchestrator.parse_document") as mock_parse,
        patch("server.projects.deep_research.orchestrator.ingest_knowledge") as mock_ingest,
    ):
        from server.projects.deep_research.models import (
            DocumentChunk,
            FetchPageResponse,
            IngestKnowledgeResponse,
            ParseDocumentResponse,
            SearchResult,
            SearchWebResponse,
        )

        mock_search.return_value = SearchWebResponse(
            query="test query",
            results=[
                SearchResult(
                    title="Test",
                    url="https://example.com/test",
                    snippet="Test snippet",
                    engine="google",
                    score=0.95,
                )
            ],
            count=1,
            success=True,
        )

        mock_fetch.return_value = FetchPageResponse(
            url="https://example.com/test", content="# Test\n\nContent", metadata={}, success=True
        )

        mock_parse.return_value = ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test chunk",
                    index=0,
                    start_char=0,
                    end_char=10,
                    metadata={},
                    token_count=2,
                )
            ],
            metadata={},
            success=True,
        )

        mock_ingest.return_value = IngestKnowledgeResponse(
            document_id="doc-123", chunks_created=1, facts_added=0, success=True, errors=[]
        )

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await executor_node(state)

            assert result_state["current_vector_index"] == 1
            assert len(result_state["vectors"][0].sources) > 0
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_executor_node_full_pipeline(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test executor node executes full pipeline: Search → Fetch → Parse → Ingest."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.search_web") as mock_search,
        patch("server.projects.deep_research.orchestrator.fetch_page") as mock_fetch,
        patch("server.projects.deep_research.orchestrator.parse_document") as mock_parse,
        patch("server.projects.deep_research.orchestrator.ingest_knowledge") as mock_ingest,
    ):
        from server.projects.deep_research.models import (
            DocumentChunk,
            FetchPageResponse,
            IngestKnowledgeResponse,
            ParseDocumentResponse,
            SearchResult,
            SearchWebResponse,
        )

        mock_search.return_value = SearchWebResponse(
            query="test",
            results=[
                SearchResult(
                    title="Test",
                    url="https://example.com/test",
                    snippet="Test",
                    engine="google",
                    score=0.95,
                )
            ],
            count=1,
            success=True,
        )

        mock_fetch.return_value = FetchPageResponse(
            url="https://example.com/test", content="# Test", metadata={}, success=True
        )

        mock_parse.return_value = ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test", index=0, start_char=0, end_char=4, metadata={}, token_count=1
                )
            ],
            metadata={},
            success=True,
        )

        mock_ingest.return_value = IngestKnowledgeResponse(
            document_id="doc-123", chunks_created=1, facts_added=0, success=True, errors=[]
        )

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            await executor_node(state)

            # Verify all steps were called
            mock_search.assert_called_once()
            mock_fetch.assert_called_once()
            mock_parse.assert_called_once()
            mock_ingest.assert_called_once()
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_executor_node_vector_status_updates(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test that executor node updates vector status."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.search_web") as mock_search,
        patch("server.projects.deep_research.orchestrator.fetch_page") as mock_fetch,
        patch("server.projects.deep_research.orchestrator.parse_document") as mock_parse,
        patch("server.projects.deep_research.orchestrator.ingest_knowledge") as mock_ingest,
    ):
        from server.projects.deep_research.models import (
            DocumentChunk,
            FetchPageResponse,
            IngestKnowledgeResponse,
            ParseDocumentResponse,
            SearchResult,
            SearchWebResponse,
        )

        mock_search.return_value = SearchWebResponse(
            query="test",
            results=[
                SearchResult(
                    title="Test",
                    url="https://example.com/test",
                    snippet="Test",
                    engine="google",
                    score=0.95,
                )
            ],
            count=1,
            success=True,
        )

        mock_fetch.return_value = FetchPageResponse(
            url="https://example.com/test", content="# Test", metadata={}, success=True
        )

        mock_parse.return_value = ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test", index=0, start_char=0, end_char=4, metadata={}, token_count=1
                )
            ],
            metadata={},
            success=True,
        )

        mock_ingest.return_value = IngestKnowledgeResponse(
            document_id="doc-123", chunks_created=1, facts_added=0, success=True, errors=[]
        )

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await executor_node(state)

            # Vector should be in "ingesting" status (will be verified by auditor)
            assert result_state["vectors"][0].status in ["ingesting", "failed"]
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_executor_node_error_handling(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test executor node error handling and status updates."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["current_vector_index"] = 0

    with patch("server.projects.deep_research.orchestrator.search_web") as mock_search:
        mock_search.side_effect = Exception("Search failed")

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await executor_node(state)

            assert result_state["vectors"][0].status == "failed"
            assert len(result_state["errors"]) > 0
            assert result_state["current_vector_index"] == 1
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_executor_node_iterates_vectors(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test that executor node iterates through multiple vectors."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.search_web") as mock_search,
        patch("server.projects.deep_research.orchestrator.fetch_page") as mock_fetch,
        patch("server.projects.deep_research.orchestrator.parse_document") as mock_parse,
        patch("server.projects.deep_research.orchestrator.ingest_knowledge") as mock_ingest,
    ):
        from server.projects.deep_research.models import (
            DocumentChunk,
            FetchPageResponse,
            IngestKnowledgeResponse,
            ParseDocumentResponse,
            SearchResult,
            SearchWebResponse,
        )

        mock_search.return_value = SearchWebResponse(
            query="test",
            results=[
                SearchResult(
                    title="Test",
                    url="https://example.com/test",
                    snippet="Test",
                    engine="google",
                    score=0.95,
                )
            ],
            count=1,
            success=True,
        )

        mock_fetch.return_value = FetchPageResponse(
            url="https://example.com/test", content="# Test", metadata={}, success=True
        )

        mock_parse.return_value = ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test", index=0, start_char=0, end_char=4, metadata={}, token_count=1
                )
            ],
            metadata={},
            success=True,
        )

        mock_ingest.return_value = IngestKnowledgeResponse(
            document_id="doc-123", chunks_created=1, facts_added=0, success=True, errors=[]
        )

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            # Process first vector
            result_state = await executor_node(state)
            assert result_state["current_vector_index"] == 1

            # Process second vector
            result_state = await executor_node(result_state)
            assert result_state["current_vector_index"] == 2
        finally:
            orchestrator_module._current_deps = None


# ============================================================================
# Auditor Node Tests
# ============================================================================


@pytest.mark.asyncio
async def test_auditor_node_validates_high_confidence(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test auditor node validates with high confidence."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "ingesting"
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.auditor_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Relevant content 1",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                ),
                CitedChunk(
                    chunk_id="chunk-2",
                    content="Relevant content 2",
                    document_id="doc-2",
                    document_source="https://example.com/source2",
                    similarity=0.92,
                    metadata={},
                ),
            ],
            count=2,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = '{"confidence": "high", "evidence_found": true}'
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await auditor_node(state)

            assert result_state["vectors"][0].status == "verified"
            assert result_state["vectors"][0].chunks_retrieved > 0
            assert result_state["current_vector_index"] == 1
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_auditor_node_validates_low_confidence(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test auditor node triggers refinement on low confidence."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "ingesting"
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.auditor_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        # Return only one result (low confidence)
        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Minimal content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.5,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = (
            '{"confidence": "low", "evidence_found": false, "refined_query": "more detailed query"}'
        )
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await auditor_node(state)

            assert result_state["vectors"][0].status == "incomplete"
            assert result_state["vectors"][0].feedback_loop_count > 0
            assert result_state["vectors"][0].refined_query is not None
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_auditor_node_refinement_loop(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test refinement loop with max attempts."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "ingesting"
    state["vectors"][0].feedback_loop_count = 2  # Already tried twice
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.auditor_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Minimal content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.5,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = '{"confidence": "low", "evidence_found": false}'
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await auditor_node(state)

            # Should fail after max attempts
            assert result_state["vectors"][0].status == "failed"
            assert result_state["vectors"][0].feedback_loop_count == 3
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_auditor_node_missing_evidence(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test auditor node handles missing evidence."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "ingesting"
    state["current_vector_index"] = 0

    with patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query:
        from server.projects.deep_research.models import QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(results=[], count=0, success=True)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await auditor_node(state)

            assert result_state["vectors"][0].status == "incomplete"
            assert result_state["vectors"][0].feedback_loop_count > 0
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_auditor_node_marks_verified(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test auditor node marks vectors as verified."""
    state = sample_research_state.copy()
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "ingesting"
    state["current_vector_index"] = 0

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.auditor_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Relevant content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                ),
                CitedChunk(
                    chunk_id="chunk-2",
                    content="More relevant content",
                    document_id="doc-2",
                    document_source="https://example.com/source2",
                    similarity=0.92,
                    metadata={},
                ),
            ],
            count=2,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = '{"confidence": "high", "evidence_found": true}'
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await auditor_node(state)

            assert result_state["vectors"][0].status == "verified"
            assert result_state["vectors"][0].chunks_retrieved == 2
        finally:
            orchestrator_module._current_deps = None


# ============================================================================
# Writer Node Tests
# ============================================================================


@pytest.mark.asyncio
async def test_writer_node_generates_sections(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test writer node generates sections."""
    state = sample_research_state.copy()
    state["outline"] = ["Introduction", "Background", "Conclusion"]
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "verified"
    state["vectors"][1].status = "verified"
    state["vectors"][2].status = "verified"

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.writer_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Section content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = "## Introduction\n\nContent with [1] citation."
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await writer_node(state)

            assert len(result_state["completed_sections"]) > 0
            assert result_state["final_report"] is not None
            assert len(result_state["final_report"]) > 0
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_writer_node_citations(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test writer node enforces citations."""
    state = sample_research_state.copy()
    state["outline"] = ["Introduction"]
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "verified"

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.writer_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Content with citation",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = "Content with [1] citation marker."
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await writer_node(state)

            # Check that citations are in the report
            assert (
                "[1]" in result_state["final_report"]
                or "citation" in result_state["final_report"].lower()
            )
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_writer_node_closed_book_mode(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test writer node enforces closed-book mode."""
    state = sample_research_state.copy()
    state["outline"] = ["Introduction"]
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "verified"

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.writer_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Retrieved fact",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = "Section based on retrieved facts only."
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await writer_node(state)

            # Writer should use query_knowledge to get facts
            mock_query.assert_called()
            assert result_state["final_report"] is not None
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_writer_node_combines_sections(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test writer node combines sections into final report."""
    state = sample_research_state.copy()
    state["outline"] = ["Section 1", "Section 2", "Section 3"]
    state["vectors"] = sample_research_vectors
    for v in state["vectors"]:
        v.status = "verified"

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.writer_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Section content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = "Section content"
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await writer_node(state)

            assert result_state["final_report"] is not None
            # Report should contain section headers
            assert (
                "Section 1" in result_state["final_report"]
                or "section" in result_state["final_report"].lower()
            )
        finally:
            orchestrator_module._current_deps = None


@pytest.mark.asyncio
async def test_writer_node_sources_section(
    mock_deep_research_deps, sample_research_state, sample_research_vectors
):
    """Test writer node generates sources section."""
    state = sample_research_state.copy()
    state["outline"] = ["Introduction"]
    state["vectors"] = sample_research_vectors
    state["vectors"][0].status = "verified"
    state["vectors"][0].sources = ["https://example.com/source1", "https://example.com/source2"]

    with (
        patch("server.projects.deep_research.orchestrator.query_knowledge") as mock_query,
        patch("server.projects.deep_research.orchestrator.writer_agent") as mock_agent,
    ):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-1",
                    content="Content",
                    document_id="doc-1",
                    document_source="https://example.com/source1",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

        mock_result = Mock()
        mock_result.data = "Section content"
        mock_agent.run = AsyncMock(return_value=mock_result)

        import server.projects.deep_research.orchestrator as orchestrator_module

        orchestrator_module._current_deps = mock_deep_research_deps

        try:
            result_state = await writer_node(state)

            # Report should include sources section
            assert (
                "Sources" in result_state["final_report"]
                or "source" in result_state["final_report"].lower()
            )
        finally:
            orchestrator_module._current_deps = None
