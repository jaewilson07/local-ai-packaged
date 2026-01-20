"""Tests for Crawl4AI RAG single page crawling."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from workflows.ingestion.crawl4ai_rag.tools import crawl_and_ingest_single_page

from tests.conftest import MockRunContext


@pytest.mark.asyncio
async def test_crawl_single_page(mock_crawl4ai_deps, sample_crawl_result):
    """Test single page crawl."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    url = "https://example.com"

    # Mock crawler
    with patch(
        "workflows.ingestion.crawl4ai_rag.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = sample_crawl_result

        # Mock ingestion
        with patch(
            "workflows.ingestion.crawl4ai_rag.tools.ContentIngestionService"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            mock_ingester.ingest_crawled_page = AsyncMock(
                return_value=Mock(chunks_created=5, document_id="doc123", errors=[])
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_single_page(
                ctx, url=url, chunk_size=1000, chunk_overlap=200
            )

            # Assert
            assert result["success"] is True
            assert result["url"] == url
            assert result["pages_crawled"] == 1
            assert result["chunks_created"] == 5
            assert result["document_id"] == "doc123"


@pytest.mark.asyncio
async def test_crawl_with_chunking(mock_crawl4ai_deps, sample_crawl_result):
    """Test crawl with custom chunking parameters."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    url = "https://example.com"

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = sample_crawl_result

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            mock_ingester.ingest_crawled_page = AsyncMock(
                return_value=Mock(chunks_created=10, document_id="doc123", errors=[])
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute with custom chunking
            result = await crawl_and_ingest_single_page(
                ctx, url=url, chunk_size=1500, chunk_overlap=300
            )

            # Assert
            assert result["success"] is True
            # Verify chunking parameters were passed
            call_args = mock_ingester.ingest_crawled_page.call_args
            assert call_args[1]["chunk_size"] == 1500
            assert call_args[1]["chunk_overlap"] == 300


@pytest.mark.asyncio
async def test_crawl_invalid_url(mock_crawl4ai_deps):
    """Test error handling for invalid URL."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    url = "not-a-valid-url"

    # Mock crawler to fail
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = None  # Crawl failed

        # Execute
        result = await crawl_and_ingest_single_page(
            ctx, url=url, chunk_size=1000, chunk_overlap=200
        )

        # Assert
        assert result["success"] is False
        assert result["pages_crawled"] == 0
        assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_crawl_ingestion(mock_crawl4ai_deps, sample_crawl_result):
    """Test automatic ingestion after crawl."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    url = "https://example.com"

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = sample_crawl_result

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            mock_ingester.ingest_crawled_page = AsyncMock(
                return_value=Mock(chunks_created=5, document_id="doc123", errors=[])
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_single_page(
                ctx, url=url, chunk_size=1000, chunk_overlap=200
            )

            # Assert - verify ingestion was called
            mock_ingester.ingest_crawled_page.assert_called_once()
            assert result["chunks_created"] > 0
            assert result["document_id"] is not None


@pytest.mark.asyncio
async def test_crawl_ingestion_error(mock_crawl4ai_deps, sample_crawl_result):
    """Test error handling during ingestion."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    url = "https://example.com"

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_single_page", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = sample_crawl_result

        # Mock ingestion error
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            mock_ingester.ingest_crawled_page = AsyncMock(
                return_value=Mock(chunks_created=0, document_id=None, errors=["Ingestion failed"])
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_single_page(
                ctx, url=url, chunk_size=1000, chunk_overlap=200
            )

            # Assert
            assert result["success"] is False
            assert len(result["errors"]) > 0
