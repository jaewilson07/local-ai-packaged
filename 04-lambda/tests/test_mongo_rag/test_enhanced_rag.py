"""Tests for MongoDB RAG enhanced features (decomposition, grading, citations, synthesis)."""

from unittest.mock import AsyncMock, Mock

import pytest
from server.projects.mongo_rag.nodes.citations import extract_citations, format_citations
from server.projects.mongo_rag.nodes.decompose import decompose_query
from server.projects.mongo_rag.nodes.grade import grade_documents
from server.projects.mongo_rag.nodes.rewrite import rewrite_query
from server.projects.mongo_rag.nodes.synthesize import synthesize_results


@pytest.mark.asyncio
async def test_query_decomposition(mock_llm_response):
    """Test query decomposition."""
    # Setup
    query = "What is authentication and how does it relate to authorization?"

    # Mock LLM client - function makes TWO calls: decision then decomposition
    mock_client = AsyncMock()

    # First call: decision response (should return "yes")
    decision_response = Mock()
    decision_response.choices = [Mock()]
    decision_response.choices[0].message.content = "yes"

    # Second call: decomposition response
    decompose_response = Mock()
    decompose_response.choices = [Mock()]
    decompose_response.choices[
        0
    ].message.content = (
        "1. What is authentication?\n2. How does authentication relate to authorization?"
    )

    # Mock to return different responses for each call
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[decision_response, decompose_response]
    )

    # Execute
    needs_decomp, sub_queries = await decompose_query(query, mock_client)

    # Assert
    assert needs_decomp is True
    assert len(sub_queries) > 1


@pytest.mark.asyncio
async def test_query_decomposition_not_needed(mock_llm_response):
    """Test query decomposition when not needed."""
    # Setup
    query = "What is authentication?"

    # Mock LLM client - first call returns "no", so function returns early
    mock_client = AsyncMock()
    decision_response = Mock()
    decision_response.choices = [Mock()]
    decision_response.choices[0].message.content = "no"
    mock_client.chat.completions.create = AsyncMock(return_value=decision_response)

    # Execute
    needs_decomp, sub_queries = await decompose_query(query, mock_client)

    # Assert
    assert needs_decomp is False
    assert len(sub_queries) == 1


@pytest.mark.asyncio
async def test_document_grading(mock_llm_response):
    """Test document grading."""
    # Setup - convert SearchResult to dicts as expected by grade_documents
    query = "authentication setup"
    search_results = [
        {
            "content": "This document explains authentication setup in detail.",
            "metadata": {},
            "chunk_id": "1",
            "document_id": "doc1",
            "similarity": 0.9,
        },
        {
            "content": "This document is about cooking recipes.",
            "metadata": {},
            "chunk_id": "2",
            "document_id": "doc2",
            "similarity": 0.7,
        },
    ]

    # Mock LLM client - function makes one call per document
    mock_client = AsyncMock()
    # First document: relevant (yes)
    response1 = Mock()
    response1.choices = [Mock()]
    response1.choices[0].message.content = "yes"
    # Second document: not relevant (no)
    response2 = Mock()
    response2.choices = [Mock()]
    response2.choices[0].message.content = "no"

    mock_client.chat.completions.create = AsyncMock(side_effect=[response1, response2])

    # Execute - returns (filtered_docs, scores)  # noqa: ERA001
    filtered_docs, scores = await grade_documents(query, search_results, mock_client)

    # Assert
    assert len(filtered_docs) > 0
    assert len(scores) == 2
    # First result should be relevant (score 1.0), second not (score 0.0)
    assert scores[0] == 1.0
    assert scores[1] == 0.0
    # Only first document should be in filtered_docs (threshold is 0.5)
    assert len(filtered_docs) == 1


@pytest.mark.asyncio
async def test_citation_extraction():
    """Test citation extraction."""
    # Setup - function expects List[Dict]
    search_results = [
        {
            "chunk_id": "1",
            "document_id": "doc1",
            "content": "Authentication is the process of verifying identity.",
            "metadata": {
                "source": "https://example.com/auth",
                "title": "Auth Guide",
                "document_title": "Auth Guide",
            },
        }
    ]

    # Execute
    citations = extract_citations(search_results)

    # Assert
    assert len(citations) > 0
    assert citations[0]["title"] == "Auth Guide"
    assert citations[0]["source"] == "https://example.com/auth"


@pytest.mark.asyncio
async def test_format_citations():
    """Test citation formatting."""
    # Setup - citation dict needs 'id' field
    citations = [
        {"id": 1, "title": "Auth Guide", "source": "https://example.com/auth", "chunk_id": "1"}
    ]

    # Execute
    formatted = format_citations(citations)

    # Assert
    assert "Auth Guide" in formatted
    assert "https://example.com/auth" in formatted


@pytest.mark.asyncio
async def test_result_synthesis(mock_llm_response):
    """Test result synthesis."""
    # Setup - function expects List[Dict] with 'query' and 'results' keys
    query = "authentication"
    sub_query_results = [
        {
            "query": "What is authentication?",
            "results": [{"content": "Authentication verifies identity.", "similarity": 0.9}],
        },
        {
            "query": "What is authorization?",
            "results": [{"content": "Authorization controls access.", "similarity": 0.8}],
        },
    ]

    # Mock LLM client
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[
        0
    ].message.content = (
        "Authentication verifies identity, while authorization controls access to resources."
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    synthesized = await synthesize_results(query, sub_query_results, mock_client)

    # Assert
    assert len(synthesized) > 0
    assert "authentication" in synthesized.lower() or "authorization" in synthesized.lower()


@pytest.mark.asyncio
async def test_query_rewriting(mock_llm_response):
    """Test query rewriting."""
    # Setup
    query = "auth setup"

    # Mock LLM client
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "How to set up authentication"
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Execute
    rewritten = await rewrite_query(query, mock_client)

    # Assert
    assert rewritten != query
    assert "authentication" in rewritten.lower() or "setup" in rewritten.lower()
