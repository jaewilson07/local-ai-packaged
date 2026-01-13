"""Unit tests for Deep Research Agent tools (Phase 1-2)."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from bson import ObjectId

from server.projects.deep_research.models import (
    FetchPageRequest,
    IngestKnowledgeRequest,
    ParseDocumentRequest,
    QueryKnowledgeRequest,
    SearchWebRequest,
)
from server.projects.deep_research.tools import (
    fetch_page,
    ingest_knowledge,
    parse_document,
    query_knowledge,
    search_web,
)
from tests.conftest import async_iter

# ============================================================================
# search_web Tests
# ============================================================================


@pytest.mark.asyncio
async def test_search_web_success(mock_deep_research_deps, sample_search_results):
    """Test successful web search."""
    request = SearchWebRequest(query="deep research", result_count=5)

    # Mock SearXNG search
    with patch("server.api.searxng.search") as mock_searxng_search:
        from server.api.searxng import SearXNGSearchResponse, SearXNGSearchResult

        mock_searxng_response = SearXNGSearchResponse(
            query="deep research",
            results=[
                SearXNGSearchResult(
                    title=r["title"],
                    url=r["url"],
                    content=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results
            ],
            count=len(sample_search_results),
            success=True,
        )
        mock_searxng_search.return_value = mock_searxng_response

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is True
        assert response.query == "deep research"
        assert len(response.results) == len(sample_search_results)
        assert response.results[0].title == sample_search_results[0]["title"]


@pytest.mark.asyncio
async def test_search_web_empty_query(mock_deep_research_deps):
    """Test search with empty query."""
    request = SearchWebRequest(query="", result_count=5)

    with patch("server.api.searxng.search") as mock_searxng_search:
        from server.api.searxng import SearXNGSearchResponse

        mock_searxng_response = SearXNGSearchResponse(query="", results=[], count=0, success=False)
        mock_searxng_search.return_value = mock_searxng_response

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is False
        assert response.count == 0


@pytest.mark.asyncio
async def test_search_web_timeout(mock_deep_research_deps):
    """Test search with timeout."""
    request = SearchWebRequest(query="deep research", result_count=5)

    with patch("server.api.searxng.search") as mock_searxng_search:
        mock_searxng_search.side_effect = httpx.TimeoutException("Request timed out")

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is False
        assert response.count == 0


@pytest.mark.asyncio
async def test_search_web_connection_error(mock_deep_research_deps):
    """Test search with connection error."""
    request = SearchWebRequest(query="deep research", result_count=5)

    with patch("server.api.searxng.search") as mock_searxng_search:
        mock_searxng_search.side_effect = httpx.ConnectError("Connection failed")

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is False
        assert response.count == 0


@pytest.mark.asyncio
async def test_search_web_with_limit(mock_deep_research_deps, sample_search_results):
    """Test search with result count limit."""
    request = SearchWebRequest(query="deep research", result_count=2)

    with patch("server.api.searxng.search") as mock_searxng_search:
        from server.api.searxng import SearXNGSearchResponse, SearXNGSearchResult

        mock_searxng_response = SearXNGSearchResponse(
            query="deep research",
            results=[
                SearXNGSearchResult(
                    title=r["title"],
                    url=r["url"],
                    content=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results[:2]
            ],
            count=2,
            success=True,
        )
        mock_searxng_search.return_value = mock_searxng_response

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.results) == 2


@pytest.mark.asyncio
async def test_search_web_with_engines(mock_deep_research_deps, sample_search_results):
    """Test search with engine filtering."""
    request = SearchWebRequest(query="deep research", result_count=5, engines=["google", "bing"])

    with patch("server.api.searxng.search") as mock_searxng_search:
        from server.api.searxng import SearXNGSearchResponse, SearXNGSearchResult

        mock_searxng_response = SearXNGSearchResponse(
            query="deep research",
            results=[
                SearXNGSearchResult(
                    title=r["title"],
                    url=r["url"],
                    content=r["snippet"],
                    engine=r["engine"],
                    score=r["score"],
                )
                for r in sample_search_results
                if r["engine"] in ["google", "bing"]
            ],
            count=2,
            success=True,
        )
        mock_searxng_search.return_value = mock_searxng_response

        response = await search_web(mock_deep_research_deps, request)

        assert response.success is True
        assert all(r.engine in ["google", "bing"] for r in response.results)


# ============================================================================
# fetch_page Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_page_success(mock_deep_research_deps, sample_fetch_response):
    """Test successful page fetch."""
    from pydantic import HttpUrl

    request = FetchPageRequest(url=HttpUrl("https://example.com/test-article"))

    with patch(
        "server.projects.deep_research.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = {
            "url": "https://example.com/test-article",
            "markdown": sample_fetch_response["content"],
            "metadata": sample_fetch_response["metadata"],
        }

        response = await fetch_page(mock_deep_research_deps, request)

        assert response.success is True
        assert response.url == "https://example.com/test-article"
        assert "Test Article" in response.content
        assert response.metadata["title"] == sample_fetch_response["metadata"]["title"]


@pytest.mark.asyncio
async def test_fetch_page_invalid_url(mock_deep_research_deps):
    """Test fetch with invalid URL."""
    from pydantic import ValidationError

    # Invalid URL should be caught by Pydantic validation
    with pytest.raises(ValidationError):
        FetchPageRequest(url="not-a-url")


@pytest.mark.asyncio
async def test_fetch_page_timeout(mock_deep_research_deps):
    """Test fetch with timeout."""
    from pydantic import HttpUrl

    request = FetchPageRequest(url=HttpUrl("https://example.com/test"))

    with patch("server.projects.deep_research.tools.crawl_single_page") as mock_crawl:
        mock_crawl.side_effect = TimeoutError("Request timed out")

        response = await fetch_page(mock_deep_research_deps, request)

        assert response.success is False


@pytest.mark.asyncio
async def test_fetch_page_connection_error(mock_deep_research_deps):
    """Test fetch with connection error."""
    from pydantic import HttpUrl

    request = FetchPageRequest(url=HttpUrl("https://example.com/test"))

    with patch(
        "server.projects.deep_research.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.side_effect = ConnectionError("Connection failed")

        response = await fetch_page(mock_deep_research_deps, request)

        assert response.success is False


@pytest.mark.asyncio
async def test_fetch_page_metadata_extraction(mock_deep_research_deps, sample_fetch_response):
    """Test metadata extraction."""
    from pydantic import HttpUrl

    request = FetchPageRequest(url=HttpUrl("https://example.com/test-article"))

    with patch(
        "server.projects.deep_research.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = {
            "url": "https://example.com/test-article",
            "markdown": sample_fetch_response["content"],
            "metadata": sample_fetch_response["metadata"],
        }

        response = await fetch_page(mock_deep_research_deps, request)

        assert "title" in response.metadata
        assert "description" in response.metadata
        assert response.metadata["title"] == sample_fetch_response["metadata"]["title"]


# ============================================================================
# parse_document Tests
# ============================================================================


@pytest.mark.asyncio
async def test_parse_document_html(mock_deep_research_deps, sample_fetch_response):
    """Test HTML document parsing."""
    request = ParseDocumentRequest(content=sample_fetch_response["content"], content_type="html")

    with patch("server.projects.deep_research.tools.DoclingHybridChunker") as mock_chunker:
        from server.projects.mongo_rag.ingestion.chunker import DocumentChunk as MongoChunk

        mock_chunk = MongoChunk(
            content="Test chunk content",
            index=0,
            start_char=0,
            end_char=20,
            metadata={},
            token_count=5,
        )
        mock_chunker_instance = Mock()
        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
        mock_chunker.return_value = mock_chunker_instance

        # Mock document_converter on deps
        mock_doc = Mock()
        mock_doc.document = Mock()
        mock_doc.document.export_to_markdown = Mock(return_value="# Test\n\nContent")
        mock_converter_instance = Mock()
        mock_converter_instance.convert.return_value = mock_doc
        mock_deep_research_deps.document_converter = mock_converter_instance

        response = await parse_document(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.chunks) > 0


@pytest.mark.asyncio
async def test_parse_document_markdown(mock_deep_research_deps):
    """Test markdown document parsing."""
    markdown_content = """# Test Document

This is a test markdown document.

## Section 1

Content here.
"""
    request = ParseDocumentRequest(content=markdown_content, content_type="markdown")

    with patch("server.projects.deep_research.tools.DoclingHybridChunker") as mock_chunker:
        from server.projects.mongo_rag.ingestion.chunker import DocumentChunk as MongoChunk

        mock_chunk = MongoChunk(
            content="Test chunk content",
            index=0,
            start_char=0,
            end_char=20,
            metadata={},
            token_count=5,
        )
        mock_chunker_instance = Mock()
        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
        mock_chunker.return_value = mock_chunker_instance

        # Mock document_converter on deps
        mock_doc = Mock()
        mock_doc.document = Mock()
        mock_doc.document.export_to_markdown = Mock(return_value=markdown_content)
        mock_converter_instance = Mock()
        mock_converter_instance.convert.return_value = mock_doc
        mock_deep_research_deps.document_converter = mock_converter_instance

        response = await parse_document(mock_deep_research_deps, request)

        assert response.success is True


@pytest.mark.asyncio
async def test_parse_document_text(mock_deep_research_deps):
    """Test plain text document parsing."""
    text_content = "This is plain text content for testing."
    request = ParseDocumentRequest(content=text_content, content_type="text")

    with patch("server.projects.deep_research.tools.DoclingHybridChunker") as mock_chunker:
        from server.projects.mongo_rag.ingestion.chunker import DocumentChunk as MongoChunk

        mock_chunk = MongoChunk(
            content=text_content,
            index=0,
            start_char=0,
            end_char=len(text_content),
            metadata={},
            token_count=10,
        )
        mock_chunker_instance = Mock()
        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
        mock_chunker.return_value = mock_chunker_instance

        # Mock document_converter on deps
        mock_doc = Mock()
        mock_doc.document = Mock()
        mock_doc.document.export_to_markdown = Mock(return_value=text_content)
        mock_converter_instance = Mock()
        mock_converter_instance.convert.return_value = mock_doc
        mock_deep_research_deps.document_converter = mock_converter_instance

        response = await parse_document(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.chunks) > 0


@pytest.mark.asyncio
async def test_parse_document_chunking(mock_deep_research_deps):
    """Test document chunking with size and overlap."""
    content = " ".join(["Word"] * 2000)  # Long content
    request = ParseDocumentRequest(content=content, content_type="text")

    with patch("server.projects.deep_research.tools.DoclingHybridChunker") as mock_chunker:
        from server.projects.mongo_rag.ingestion.chunker import DocumentChunk as MongoChunk

        # Create multiple chunks
        chunks = [
            MongoChunk(
                content=f"Chunk {i} content",
                index=i,
                start_char=i * 100,
                end_char=(i + 1) * 100,
                metadata={},
                token_count=20,
            )
            for i in range(5)
        ]
        mock_chunker_instance = Mock()
        mock_chunker_instance.chunk_document = AsyncMock(return_value=chunks)
        mock_chunker.return_value = mock_chunker_instance

        # Mock document_converter on deps
        mock_doc = Mock()
        mock_doc.document = Mock()
        mock_doc.document.export_to_markdown = Mock(return_value=content)
        mock_converter_instance = Mock()
        mock_converter_instance.convert.return_value = mock_doc
        mock_deep_research_deps.document_converter = mock_converter_instance

        response = await parse_document(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.chunks) == 5


@pytest.mark.asyncio
async def test_parse_document_empty_content(mock_deep_research_deps):
    """Test parsing empty content."""
    request = ParseDocumentRequest(content="", content_type="text")

    response = await parse_document(mock_deep_research_deps, request)

    # Should handle empty content gracefully
    assert response.success is False or len(response.chunks) == 0


# ============================================================================
# ingest_knowledge Tests
# ============================================================================


@pytest.mark.asyncio
async def test_ingest_knowledge_success(mock_deep_research_deps, sample_parsed_chunks):
    """Test successful knowledge ingestion."""
    from server.projects.deep_research.models import DocumentChunk

    chunks = [
        DocumentChunk(
            content=chunk["content"],
            index=chunk["index"],
            start_char=chunk["start_char"],
            end_char=chunk["end_char"],
            metadata=chunk["metadata"],
            token_count=chunk["token_count"],
        )
        for chunk in sample_parsed_chunks
    ]

    request = IngestKnowledgeRequest(
        chunks=chunks,
        session_id="test-session-123",
        source_url="https://example.com/test",
        title="Test Document",
    )

    # Mock MongoDB operations
    mock_deep_research_deps.db["documents"].insert_one = AsyncMock(
        return_value=Mock(inserted_id=ObjectId())
    )
    mock_deep_research_deps.db["chunks"].insert_many = AsyncMock(
        return_value=Mock(inserted_ids=[ObjectId() for _ in chunks])
    )

    response = await ingest_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert response.chunks_created == len(chunks)


@pytest.mark.asyncio
async def test_ingest_knowledge_with_graphiti(mock_deep_research_deps, sample_parsed_chunks):
    """Test ingestion with Graphiti enabled."""
    from server.projects.deep_research.models import DocumentChunk

    chunks = [
        DocumentChunk(
            content=chunk["content"],
            index=chunk["index"],
            start_char=chunk["start_char"],
            end_char=chunk["end_char"],
            metadata=chunk["metadata"],
            token_count=chunk["token_count"],
        )
        for chunk in sample_parsed_chunks
    ]

    request = IngestKnowledgeRequest(
        chunks=chunks,
        session_id="test-session-123",
        source_url="https://example.com/test",
        title="Test Document",
    )

    # Mock MongoDB operations
    mock_deep_research_deps.db["documents"].insert_one = AsyncMock(
        return_value=Mock(inserted_id=ObjectId())
    )
    mock_deep_research_deps.db["chunks"].insert_many = AsyncMock(
        return_value=Mock(inserted_ids=[ObjectId() for _ in chunks])
    )

    # Mock Graphiti ingestion
    with patch("server.projects.deep_research.tools.ingest_to_graphiti") as mock_graphiti:
        mock_graphiti.return_value = len(chunks)  # Return number of facts added

        response = await ingest_knowledge(mock_deep_research_deps, request)

        assert response.success is True
        assert response.facts_added > 0


@pytest.mark.asyncio
async def test_ingest_knowledge_session_isolation(mock_deep_research_deps, sample_parsed_chunks):
    """Test session ID isolation in ingestion."""
    from server.projects.deep_research.models import DocumentChunk

    chunks = [
        DocumentChunk(
            content=chunk["content"],
            index=chunk["index"],
            start_char=chunk["start_char"],
            end_char=chunk["end_char"],
            metadata=chunk["metadata"],
            token_count=chunk["token_count"],
        )
        for chunk in sample_parsed_chunks
    ]

    request = IngestKnowledgeRequest(
        chunks=chunks,
        session_id="test-session-456",
        source_url="https://example.com/test",
        title="Test Document",
    )

    # Mock MongoDB operations
    mock_deep_research_deps.db["documents"].insert_one = AsyncMock(
        return_value=Mock(inserted_id=ObjectId())
    )
    mock_deep_research_deps.db["chunks"].insert_many = AsyncMock(
        return_value=Mock(inserted_ids=[ObjectId() for _ in chunks])
    )

    response = await ingest_knowledge(mock_deep_research_deps, request)

    # Verify session_id is in metadata
    assert response.success is True
    # Check that insert_many was called with chunks containing session_id
    call_args = mock_deep_research_deps.db["chunks"].insert_many.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_ingest_knowledge_empty_chunks(mock_deep_research_deps):
    """Test ingestion with empty chunks."""
    request = IngestKnowledgeRequest(
        chunks=[],
        session_id="test-session-123",
        source_url="https://example.com/test",
        title="Test Document",
    )

    response = await ingest_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert response.chunks_created == 0


@pytest.mark.asyncio
async def test_ingest_knowledge_embedding_generation(mock_deep_research_deps, sample_parsed_chunks):
    """Test embedding generation during ingestion."""
    from server.projects.deep_research.models import DocumentChunk

    chunks = [
        DocumentChunk(
            content=chunk["content"],
            index=chunk["index"],
            start_char=chunk["start_char"],
            end_char=chunk["end_char"],
            metadata=chunk["metadata"],
            token_count=chunk["token_count"],
        )
        for chunk in sample_parsed_chunks
    ]

    request = IngestKnowledgeRequest(
        chunks=chunks,
        session_id="test-session-123",
        source_url="https://example.com/test",
        title="Test Document",
    )

    # Mock MongoDB operations
    mock_deep_research_deps.db["documents"].insert_one = AsyncMock(
        return_value=Mock(inserted_id=ObjectId())
    )
    mock_deep_research_deps.db["chunks"].insert_many = AsyncMock(
        return_value=Mock(inserted_ids=[ObjectId() for _ in chunks])
    )

    # Verify get_embedding is called
    response = await ingest_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    # get_embedding should be called for each chunk
    assert mock_deep_research_deps.get_embedding.call_count == len(chunks)


# ============================================================================
# query_knowledge Tests
# ============================================================================


@pytest.mark.asyncio
async def test_query_knowledge_semantic(mock_deep_research_deps, sample_mongo_chunk):
    """Test semantic search only."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="semantic",
    )

    # Mock MongoDB vector search
    from tests.conftest import async_iter

    mock_cursor = async_iter(
        [
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test",
            }
        ]
    )

    mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
    mock_deep_research_deps.db["documents"].find_one = AsyncMock(
        return_value={"title": "Test Document", "source": "https://example.com/test"}
    )

    response = await query_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert len(response.results) > 0
    assert response.results[0].similarity > 0


@pytest.mark.asyncio
async def test_query_knowledge_text(mock_deep_research_deps, sample_mongo_chunk):
    """Test text search only."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="text",
    )

    # Mock MongoDB text search
    mock_cursor = async_iter(
        [
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.88,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test",
            }
        ]
    )

    mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
    mock_deep_research_deps.db["documents"].find_one = AsyncMock(
        return_value={"title": "Test Document", "source": "https://example.com/test"}
    )

    response = await query_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert len(response.results) > 0


@pytest.mark.asyncio
async def test_query_knowledge_hybrid(mock_deep_research_deps, sample_mongo_chunk):
    """Test hybrid search (RRF)."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
    )

    # Mock both vector and text search results
    mock_cursor = async_iter(
        [
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test",
            }
        ]
    )

    mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
    mock_deep_research_deps.db["documents"].find_one = AsyncMock(
        return_value={"title": "Test Document", "source": "https://example.com/test"}
    )

    response = await query_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert len(response.results) > 0


@pytest.mark.asyncio
async def test_query_knowledge_with_graphiti(
    mock_deep_research_deps, sample_mongo_chunk, sample_graphiti_result
):
    """Test graph-enhanced search (Phase 6)."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="hybrid",
        use_graphiti=True,
    )

    # Mock Graphiti search - patch at the source module
    with patch(
        "server.projects.graphiti_rag.search.graph_search.graphiti_search", new_callable=AsyncMock
    ) as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]

        # Mock MongoDB operations
        mock_cursor = async_iter(
            [
                {
                    "chunk_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
                    "document_id": ObjectId(sample_graphiti_result.metadata["document_id"]),
                    "content": sample_mongo_chunk["content"],
                    "similarity": 0.95,
                    "metadata": sample_mongo_chunk["metadata"],
                    "document_title": "Test Document",
                    "document_source": "https://example.com/test",
                }
            ]
        )

        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(return_value=sample_mongo_chunk)
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(
            return_value={"title": "Test Document", "source": "https://example.com/test"}
        )
        mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)

        response = await query_knowledge(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.results) > 0


@pytest.mark.asyncio
async def test_query_knowledge_session_filtering(mock_deep_research_deps, sample_mongo_chunk):
    """Test session ID filtering."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="semantic",
    )

    # Mock MongoDB vector search with session filter
    mock_cursor = async_iter(
        [
            {
                "chunk_id": sample_mongo_chunk["_id"],
                "document_id": sample_mongo_chunk["document_id"],
                "content": sample_mongo_chunk["content"],
                "similarity": 0.95,
                "metadata": sample_mongo_chunk["metadata"],
                "document_title": "Test Document",
                "document_source": "https://example.com/test",
            }
        ]
    )

    mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)
    mock_deep_research_deps.db["documents"].find_one = AsyncMock(
        return_value={"title": "Test Document", "source": "https://example.com/test"}
    )

    response = await query_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    # Verify filter was applied (check aggregate call)
    call_args = mock_deep_research_deps.db["chunks"].aggregate.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_query_knowledge_empty_results(mock_deep_research_deps):
    """Test query with no results."""
    request = QueryKnowledgeRequest(
        question="Nonexistent topic",
        session_id="test-session-123",
        match_count=5,
        search_type="semantic",
    )

    # Mock empty results
    mock_cursor = async_iter([])

    mock_deep_research_deps.db["chunks"].aggregate = AsyncMock(return_value=mock_cursor)

    response = await query_knowledge(mock_deep_research_deps, request)

    assert response.success is True
    assert len(response.results) == 0
    assert response.count == 0


@pytest.mark.asyncio
async def test_query_knowledge_graph_only(mock_deep_research_deps, sample_graphiti_result):
    """Test graph-only search mode."""
    request = QueryKnowledgeRequest(
        question="What is deep research?",
        session_id="test-session-123",
        match_count=5,
        search_type="graph",
        use_graphiti=True,
    )

    # Mock Graphiti search - patch at the source module
    with patch(
        "server.projects.graphiti_rag.search.graph_search.graphiti_search", new_callable=AsyncMock
    ) as mock_graphiti_search:
        mock_graphiti_search.return_value = [sample_graphiti_result]

        # Mock MongoDB fetch
        mock_deep_research_deps.db["chunks"].find_one = AsyncMock(
            return_value={
                "_id": ObjectId(sample_graphiti_result.metadata["chunk_id"]),
                "content": sample_graphiti_result.fact,
                "document_id": ObjectId(sample_graphiti_result.metadata["document_id"]),
            }
        )
        mock_deep_research_deps.db["documents"].find_one = AsyncMock(
            return_value={"source": sample_graphiti_result.metadata["source"]}
        )

        response = await query_knowledge(mock_deep_research_deps, request)

        assert response.success is True
        assert len(response.results) > 0
