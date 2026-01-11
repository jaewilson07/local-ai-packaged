"""Tests for Linear Researcher Agent (Phase 3)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pydantic_ai import RunResult

from server.projects.deep_research.agent import linear_researcher_agent
from server.projects.deep_research.workflow import run_linear_research
from server.projects.deep_research.models import ResearchResponse
from server.projects.deep_research.dependencies import DeepResearchDeps


# ============================================================================
# Workflow Tests
# ============================================================================

@pytest.mark.asyncio
async def test_run_linear_research_success(mock_deep_research_deps):
    """Test successful end-to-end linear research workflow."""
    query = "What is deep research?"
    
    # Mock agent.run to return a successful response
    mock_result = Mock()
    mock_result.data = ResearchResponse(
        answer="Deep research is a comprehensive methodology for investigation.",
        sources=["https://example.com/source1"],
        citations=["[1]"],
        session_id="test-session-123"
    )
    mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    mock_result.tools_used = []
    
    with patch.object(linear_researcher_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result
        
        result = await run_linear_research(query)
        
        assert result.data.success is True
        assert len(result.data.answer) > 0
        assert len(result.data.sources) > 0
        assert result.data.session_id is not None


@pytest.mark.asyncio
async def test_run_linear_research_with_sources(mock_deep_research_deps):
    """Test that sources are collected correctly."""
    query = "What is deep research?"
    
    mock_result = Mock()
    mock_result.data = ResearchResponse(
        answer="Answer with sources",
        sources=[
            "https://example.com/source1",
            "https://example.com/source2",
            "https://example.com/source3"
        ],
        citations=["[1]", "[2]", "[3]"],
        session_id="test-session-123"
    )
    mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    mock_result.tools_used = []
    
    with patch.object(linear_researcher_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result
        
        result = await run_linear_research(query)
        
        assert len(result.data.sources) == 3
        assert all(source.startswith("http") for source in result.data.sources)


@pytest.mark.asyncio
async def test_run_linear_research_with_citations(mock_deep_research_deps):
    """Test that citations are generated correctly."""
    query = "What is deep research?"
    
    mock_result = Mock()
    mock_result.data = ResearchResponse(
        answer="Answer with [1] citation and [2] another citation.",
        sources=["https://example.com/source1", "https://example.com/source2"],
        citations=["[1]", "[2]"],
        session_id="test-session-123"
    )
    mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    mock_result.tools_used = []
    
    with patch.object(linear_researcher_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result
        
        result = await run_linear_research(query)
        
        assert len(result.data.citations) > 0
        assert "[1]" in result.data.answer or "[2]" in result.data.answer


@pytest.mark.asyncio
async def test_run_linear_research_error_handling(mock_deep_research_deps):
    """Test error handling and recovery."""
    query = "What is deep research?"
    
    # Mock agent.run to raise an exception
    with patch.object(linear_researcher_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = Exception("Agent execution failed")
        
        result = await run_linear_research(query)
        
        assert result.data.success is False
        assert len(result.data.errors) > 0
        assert result.data.answer == "" or "Error" in result.data.answer


@pytest.mark.asyncio
async def test_run_linear_research_session_isolation(mock_deep_research_deps):
    """Test session ID isolation."""
    query = "What is deep research?"
    
    mock_result = Mock()
    mock_result.data = ResearchResponse(
        answer="Answer",
        sources=[],
        citations=[],
        session_id="custom-session-456"
    )
    mock_result.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    mock_result.tools_used = []
    
    with patch.object(linear_researcher_agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_result
        
        result = await run_linear_research(query, session_id="custom-session-456")
        
        assert result.data.session_id == "custom-session-456"


# ============================================================================
# Agent Tool Tests
# ============================================================================

@pytest.mark.asyncio
async def test_search_web_tool(mock_deep_research_deps):
    """Test Pydantic-AI tool wrapper for search_web."""
    from server.projects.deep_research.agent import search_web_tool
    from pydantic_ai import RunContext
    
    ctx = RunContext(
        deps=mock_deep_research_deps,
        state={},
        agent=None,
        run_id="test-run"
    )
    
    with patch("server.projects.deep_research.agent.search_web") as mock_search:
        from server.projects.deep_research.models import SearchWebResponse, SearchResult
        
        mock_search.return_value = SearchWebResponse(
            query="test query",
            results=[
                SearchResult(
                    title="Test Result",
                    url="https://example.com/test",
                    snippet="Test snippet",
                    engine="google",
                    score=0.95
                )
            ],
            count=1,
            success=True
        )
        
        result = await search_web_tool(ctx, query="test query", result_count=5)
        
        assert result.success is True
        assert len(result.results) > 0


@pytest.mark.asyncio
async def test_fetch_page_tool(mock_deep_research_deps):
    """Test Pydantic-AI tool wrapper for fetch_page."""
    from server.projects.deep_research.agent import fetch_page_tool
    from pydantic_ai import RunContext
    from pydantic import HttpUrl
    
    ctx = RunContext(
        deps=mock_deep_research_deps,
        state={},
        agent=None,
        run_id="test-run"
    )
    
    with patch("server.projects.deep_research.agent.fetch_page") as mock_fetch:
        from server.projects.deep_research.models import FetchPageResponse
        
        mock_fetch.return_value = FetchPageResponse(
            url="https://example.com/test",
            content="# Test Page\n\nContent",
            metadata={"title": "Test Page"},
            success=True
        )
        
        result = await fetch_page_tool(ctx, url=HttpUrl("https://example.com/test"))
        
        assert result.success is True
        assert len(result.content) > 0


@pytest.mark.asyncio
async def test_parse_document_tool(mock_deep_research_deps):
    """Test Pydantic-AI tool wrapper for parse_document."""
    from server.projects.deep_research.agent import parse_document_tool
    from pydantic_ai import RunContext
    
    ctx = RunContext(
        deps=mock_deep_research_deps,
        state={},
        agent=None,
        run_id="test-run"
    )
    
    with patch("server.projects.deep_research.agent.parse_document") as mock_parse:
        from server.projects.deep_research.models import ParseDocumentResponse, DocumentChunk
        
        mock_parse.return_value = ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test chunk",
                    index=0,
                    start_char=0,
                    end_char=10,
                    metadata={},
                    token_count=2
                )
            ],
            metadata={},
            success=True
        )
        
        result = await parse_document_tool(ctx, content="# Test\n\nContent", content_type="html")
        
        assert result.success is True
        assert len(result.chunks) > 0


@pytest.mark.asyncio
async def test_ingest_knowledge_tool(mock_deep_research_deps):
    """Test Pydantic-AI tool wrapper for ingest_knowledge."""
    from server.projects.deep_research.agent import ingest_knowledge_tool
    from pydantic_ai import RunContext
    from pydantic import HttpUrl
    
    ctx = RunContext(
        deps=mock_deep_research_deps,
        state={},
        agent=None,
        run_id="test-run"
    )
    
    with patch("server.projects.deep_research.agent.ingest_knowledge") as mock_ingest:
        from server.projects.deep_research.models import IngestKnowledgeResponse, DocumentChunk
        
        mock_ingest.return_value = IngestKnowledgeResponse(
            document_id="doc-123",
            chunks_created=3,
            facts_added=0,
            success=True,
            errors=[]
        )
        
        chunks = [
            DocumentChunk(
                content="Chunk 1",
                index=0,
                start_char=0,
                end_char=7,
                metadata={},
                token_count=2
            )
        ]
        
        result = await ingest_knowledge_tool(
            ctx,
            chunks=chunks,
            session_id="test-session",
            source_url=HttpUrl("https://example.com/test"),
            title="Test Document"
        )
        
        assert result.success is True
        assert result.chunks_created > 0


@pytest.mark.asyncio
async def test_query_knowledge_tool(mock_deep_research_deps):
    """Test Pydantic-AI tool wrapper for query_knowledge."""
    from server.projects.deep_research.agent import query_knowledge_tool
    from pydantic_ai import RunContext
    
    ctx = RunContext(
        deps=mock_deep_research_deps,
        state={},
        agent=None,
        run_id="test-run"
    )
    
    with patch("server.projects.deep_research.agent.query_knowledge") as mock_query:
        from server.projects.deep_research.models import QueryKnowledgeResponse, CitedChunk
        
        mock_query.return_value = QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-123",
                    content="Test chunk content",
                    document_id="doc-123",
                    document_source="https://example.com/test",
                    similarity=0.95,
                    metadata={}
                )
            ],
            count=1,
            success=True
        )
        
        result = await query_knowledge_tool(
            ctx,
            question="What is deep research?",
            session_id="test-session",
            match_count=5,
            search_type="hybrid"
        )
        
        assert result.success is True
        assert len(result.results) > 0
