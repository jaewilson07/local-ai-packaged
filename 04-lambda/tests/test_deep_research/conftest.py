"""Shared pytest fixtures for Deep Research tests."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from bson import ObjectId

# Set minimal environment variables before any imports
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_db")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")
os.environ.setdefault("SEARXNG_URL", "http://localhost:8081")

import pytest

# ============================================================================
# DeepResearchDeps Fixtures
# ============================================================================


@pytest.fixture
def mock_deep_research_deps(
    mock_mongo_db, mock_embedding, mock_openai_client, mock_graphiti_rag_deps
):
    """Mock DeepResearchDeps with all dependencies."""
    from server.projects.deep_research.dependencies import DeepResearchDeps

    deps = AsyncMock(spec=DeepResearchDeps)
    deps.db = mock_mongo_db
    deps.mongo_client = AsyncMock()
    deps.http_client = AsyncMock()
    deps.crawler = AsyncMock()
    deps.document_converter = Mock()
    deps.settings = Mock(
        searxng_url="http://localhost:8081",
        browser_headless=True,
        default_chunk_size=1000,
        default_chunk_overlap=200,
    )
    deps.graphiti_deps = mock_graphiti_rag_deps
    deps.session_id = "test-session-123"
    deps.get_embedding = AsyncMock(side_effect=mock_embedding)
    deps.embedding_client = mock_openai_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()

    return deps


@pytest.fixture
def mock_deep_research_deps_no_graphiti(mock_mongo_db, mock_embedding, mock_openai_client):
    """Mock DeepResearchDeps without Graphiti."""
    from server.projects.deep_research.dependencies import DeepResearchDeps

    deps = AsyncMock(spec=DeepResearchDeps)
    deps.db = mock_mongo_db
    deps.mongo_client = AsyncMock()
    deps.http_client = AsyncMock()
    deps.crawler = AsyncMock()
    deps.document_converter = Mock()
    deps.settings = Mock(
        searxng_url="http://localhost:8081",
        browser_headless=True,
        default_chunk_size=1000,
        default_chunk_overlap=200,
    )
    deps.graphiti_deps = None
    deps.session_id = "test-session-123"
    deps.get_embedding = AsyncMock(side_effect=mock_embedding)
    deps.embedding_client = mock_openai_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()

    return deps


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_search_result():
    """Sample SearXNG search result."""
    return {
        "title": "Test Article - Deep Research",
        "url": "https://example.com/test-article",
        "snippet": "This is a test article about deep research methodologies.",
        "engine": "google",
        "score": 0.95,
    }


@pytest.fixture
def sample_search_results(sample_search_result):
    """Multiple sample search results."""
    return [
        sample_search_result,
        {
            "title": "Another Test Article",
            "url": "https://example.com/another-article",
            "snippet": "Another test article with relevant content.",
            "engine": "bing",
            "score": 0.88,
        },
        {
            "title": "Third Test Article",
            "url": "https://example.com/third-article",
            "snippet": "Third test article with additional information.",
            "engine": "duckduckgo",
            "score": 0.82,
        },
    ]


@pytest.fixture
def sample_fetch_response():
    """Sample page fetch response."""
    return {
        "url": "https://example.com/test-article",
        "content": """# Test Article

This is a test article about deep research methodologies.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
""",
        "metadata": {
            "title": "Test Article - Deep Research",
            "description": "A test article",
            "language": "en",
        },
    }


@pytest.fixture
def sample_parsed_chunks():
    """Sample document chunks from Docling."""
    return [
        {
            "content": "This is a test article about deep research methodologies.",
            "index": 0,
            "start_char": 0,
            "end_char": 60,
            "metadata": {"section": "introduction"},
            "token_count": 10,
        },
        {
            "content": "Content for section 1.",
            "index": 1,
            "start_char": 61,
            "end_char": 85,
            "metadata": {"section": "section1"},
            "token_count": 5,
        },
        {
            "content": "Content for section 2.",
            "index": 2,
            "start_char": 86,
            "end_char": 110,
            "metadata": {"section": "section2"},
            "token_count": 5,
        },
    ]


@pytest.fixture
def sample_research_state():
    """Initial ResearchState for testing."""
    return {
        "user_query": "What is deep research?",
        "outline": [],
        "vectors": [],
        "knowledge_graph_session_id": "test-session-123",
        "completed_sections": {},
        "final_report": None,
        "errors": [],
        "current_vector_index": 0,
        "max_iterations": 10,
        "iteration_count": 0,
    }


@pytest.fixture
def sample_research_vector():
    """Sample ResearchVector for node testing."""
    from server.projects.deep_research.state import ResearchVector

    return ResearchVector(
        id="v1",
        topic="What is deep research?",
        search_queries=["deep research methodology", "research techniques"],
        status="pending",
        feedback_loop_count=0,
    )


@pytest.fixture
def sample_research_vectors(sample_research_vector):
    """Multiple research vectors."""
    from server.projects.deep_research.state import ResearchVector

    return [
        sample_research_vector,
        ResearchVector(
            id="v2",
            topic="How does deep research work?",
            search_queries=["deep research process", "research workflow"],
            status="pending",
            feedback_loop_count=0,
        ),
        ResearchVector(
            id="v3",
            topic="What are the benefits of deep research?",
            search_queries=["deep research benefits", "research advantages"],
            status="pending",
            feedback_loop_count=0,
        ),
    ]


# ============================================================================
# Tool Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_search_web():
    """Mocked search_web function."""

    async def _mock_search_web(deps, request):
        from server.projects.deep_research.models import SearchResult, SearchWebResponse

        return SearchWebResponse(
            query=request.query,
            results=[
                SearchResult(
                    title="Test Result",
                    url="https://example.com/test",
                    snippet="Test snippet",
                    engine="google",
                    score=0.95,
                )
            ],
            count=1,
            success=True,
        )

    return _mock_search_web


@pytest.fixture
def mock_fetch_page():
    """Mocked fetch_page function."""

    async def _mock_fetch_page(deps, request):
        from server.projects.deep_research.models import FetchPageResponse

        return FetchPageResponse(
            url=str(request.url),
            content="# Test Page\n\nTest content here.",
            metadata={"title": "Test Page", "description": "A test page"},
            success=True,
        )

    return _mock_fetch_page


@pytest.fixture
def mock_parse_document():
    """Mocked parse_document function."""

    async def _mock_parse_document(deps, request):
        from server.projects.deep_research.models import DocumentChunk, ParseDocumentResponse

        return ParseDocumentResponse(
            chunks=[
                DocumentChunk(
                    content="Test chunk content",
                    index=0,
                    start_char=0,
                    end_char=20,
                    metadata={},
                    token_count=5,
                )
            ],
            metadata={"title": "Test Document"},
            success=True,
        )

    return _mock_parse_document


@pytest.fixture
def mock_ingest_knowledge():
    """Mocked ingest_knowledge function."""

    async def _mock_ingest_knowledge(deps, request):
        from server.projects.deep_research.models import IngestKnowledgeResponse

        return IngestKnowledgeResponse(
            document_id="test-doc-123",
            chunks_created=len(request.chunks),
            facts_added=0,
            success=True,
            errors=[],
        )

    return _mock_ingest_knowledge


@pytest.fixture
def mock_query_knowledge():
    """Mocked query_knowledge function."""

    async def _mock_query_knowledge(deps, request):
        from server.projects.deep_research.models import CitedChunk, QueryKnowledgeResponse

        return QueryKnowledgeResponse(
            results=[
                CitedChunk(
                    chunk_id="chunk-123",
                    content="Test chunk content",
                    document_id="doc-123",
                    document_source="https://example.com/test",
                    similarity=0.95,
                    metadata={},
                )
            ],
            count=1,
            success=True,
        )

    return _mock_query_knowledge


# ============================================================================
# LangGraph Agent Mocks
# ============================================================================


@pytest.fixture
def mock_planner_agent():
    """Mocked planner Pydantic-AI agent."""
    agent = AsyncMock()
    mock_result = Mock()
    mock_result.data = '{"outline": ["Introduction", "Background", "Conclusion"], "vectors": [{"id": "v1", "topic": "Test", "search_queries": ["test"]}]}'
    agent.run = AsyncMock(return_value=mock_result)
    return agent


@pytest.fixture
def mock_executor_agent():
    """Mocked executor Pydantic-AI agent."""
    agent = AsyncMock()
    mock_result = Mock()
    mock_result.data = "Executor completed successfully"
    agent.run = AsyncMock(return_value=mock_result)
    return agent


@pytest.fixture
def mock_auditor_agent():
    """Mocked auditor Pydantic-AI agent."""
    agent = AsyncMock()
    mock_result = Mock()
    mock_result.data = '{"confidence": "high", "evidence_found": true}'
    agent.run = AsyncMock(return_value=mock_result)
    return agent


@pytest.fixture
def mock_writer_agent():
    """Mocked writer Pydantic-AI agent."""
    agent = AsyncMock()
    mock_result = Mock()
    mock_result.data = "## Test Section\n\nTest content with [1] citation."
    agent.run = AsyncMock(return_value=mock_result)
    return agent


# ============================================================================
# MongoDB Mock Data
# ============================================================================


@pytest.fixture
def sample_mongo_chunk():
    """Sample MongoDB chunk document."""
    return {
        "_id": ObjectId(),
        "document_id": ObjectId(),
        "content": "Test chunk content about deep research",
        "embedding": [0.1] * 768,
        "metadata": {
            "session_id": "test-session-123",
            "source_url": "https://example.com/test",
            "chunk_index": 0,
        },
    }


@pytest.fixture
def sample_mongo_document():
    """Sample MongoDB document."""
    return {
        "_id": ObjectId(),
        "title": "Test Document",
        "source": "https://example.com/test",
        "metadata": {"session_id": "test-session-123"},
    }


# ============================================================================
# Graphiti Mock Data
# ============================================================================


@pytest.fixture
def sample_graphiti_result():
    """Sample Graphiti search result."""
    result = SimpleNamespace()
    result.fact = "Deep research is a methodology for comprehensive investigation"
    result.score = 0.9
    result.similarity = 0.9
    result.metadata = {
        "chunk_id": "chunk-123",
        "document_id": "doc-123",
        "source": "https://example.com/test",
    }
    result.content = result.fact
    return result


# ============================================================================
# HTTP Client Mocks
# ============================================================================


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response."""
    response = Mock()
    response.status_code = 200
    response.json = Mock(
        return_value={
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com/test",
                    "content": "Test content",
                    "engine": "google",
                }
            ],
            "number_of_results": 1,
        }
    )
    response.text = "# Test Page\n\nTest content"
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_httpx_client(mock_httpx_response):
    """Mock httpx.AsyncClient."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_httpx_response)
    client.post = AsyncMock(return_value=mock_httpx_response)
    client.aclose = AsyncMock()
    return client


# ============================================================================
# Crawl4AI Mocks
# ============================================================================


@pytest.fixture
def mock_crawler():
    """Mock Crawl4AI crawler."""
    crawler = AsyncMock()
    mock_crawl_result = Mock()
    mock_crawl_result.markdown = "# Test Page\n\nTest content"
    mock_crawl_result.html = "<html><body><h1>Test Page</h1></body></html>"
    mock_crawl_result.metadata = {"title": "Test Page", "description": "A test page"}
    crawler.arun = AsyncMock(return_value=mock_crawl_result)
    crawler.__aenter__ = AsyncMock(return_value=crawler)
    crawler.__aexit__ = AsyncMock(return_value=None)
    return crawler


# ============================================================================
# Docling Mocks
# ============================================================================


@pytest.fixture
def mock_document_converter():
    """Mock Docling document converter."""
    converter = Mock()
    mock_doc = Mock()
    mock_doc.document = Mock()
    converter.convert = Mock(return_value=mock_doc)
    return converter
