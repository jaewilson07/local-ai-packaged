"""Tests for Crawl4AI RAG deep recursive crawling."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from server.projects.crawl4ai_rag.tools import crawl_and_ingest_deep
from tests.conftest import MockRunContext


@pytest.mark.asyncio
async def test_deep_crawl_basic(mock_crawl4ai_deps):
    """Test basic deep crawl."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"

    # Mock deep crawl results
    crawl_results = [
        {"url": "https://example.com", "markdown": "# Page 1", "metadata": {"title": "Page 1"}},
        {
            "url": "https://example.com/page2",
            "markdown": "# Page 2",
            "metadata": {"title": "Page 2"},
        },
    ]

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = crawl_results

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            # ingest_crawled_batch returns a list of results
            mock_ingester.ingest_crawled_batch = AsyncMock(
                return_value=[
                    Mock(chunks_created=5, document_id="doc123", errors=[]),
                    Mock(chunks_created=5, document_id="doc456", errors=[]),
                ]
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_deep(
                ctx,
                start_url=start_url,
                max_depth=2,
                allowed_domains=None,
                allowed_subdomains=None,
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Assert
            assert result["success"] is True
            assert result["pages_crawled"] == len(crawl_results)
            assert result["chunks_created"] > 0


@pytest.mark.asyncio
async def test_deep_crawl_with_domain_filter(mock_crawl4ai_deps):
    """Test deep crawl with domain filtering."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"
    allowed_domains = ["example.com"]

    # Mock filtered crawl results
    crawl_results = [
        {"url": "https://example.com", "markdown": "# Page 1", "metadata": {"title": "Page 1"}}
    ]

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = crawl_results

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            # ingest_crawled_batch returns a list of results
            mock_ingester.ingest_crawled_batch = AsyncMock(
                return_value=[
                    Mock(chunks_created=5, document_id="doc123", errors=[]),
                    Mock(chunks_created=5, document_id="doc456", errors=[]),
                ]
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_deep(
                ctx,
                start_url=start_url,
                max_depth=2,
                allowed_domains=allowed_domains,
                allowed_subdomains=None,
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Assert
            assert result["success"] is True
            # Verify domain filter was applied
            call_args = mock_crawl.call_args
            assert call_args[1]["allowed_domains"] == allowed_domains


@pytest.mark.asyncio
async def test_deep_crawl_with_subdomain_filter(mock_crawl4ai_deps):
    """Test deep crawl with subdomain filtering."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"
    allowed_subdomains = ["docs", "api"]

    # Mock filtered crawl results
    crawl_results = [
        {
            "url": "https://docs.example.com",
            "markdown": "# Docs Page",
            "metadata": {"title": "Docs"},
        }
    ]

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = crawl_results

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            # ingest_crawled_batch returns a list of results
            mock_ingester.ingest_crawled_batch = AsyncMock(
                return_value=[
                    Mock(chunks_created=5, document_id="doc123", errors=[]),
                    Mock(chunks_created=5, document_id="doc456", errors=[]),
                ]
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_deep(
                ctx,
                start_url=start_url,
                max_depth=2,
                allowed_domains=None,
                allowed_subdomains=allowed_subdomains,
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Assert
            assert result["success"] is True
            # Verify subdomain filter was applied
            call_args = mock_crawl.call_args
            assert call_args[1]["allowed_subdomains"] == allowed_subdomains


@pytest.mark.asyncio
async def test_deep_crawl_depth_limit(mock_crawl4ai_deps):
    """Test deep crawl respects depth limit."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"
    max_depth = 2

    # Mock crawl results
    crawl_results = [
        {
            "url": "https://example.com",
            "markdown": "# Page 1",
            "metadata": {"title": "Page 1", "depth": 0},
        },
        {
            "url": "https://example.com/page2",
            "markdown": "# Page 2",
            "metadata": {"title": "Page 2", "depth": 1},
        },
    ]

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = crawl_results

        # Mock ingestion
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            # ingest_crawled_batch returns a list of results
            mock_ingester.ingest_crawled_batch = AsyncMock(
                return_value=[
                    Mock(chunks_created=5, document_id="doc123", errors=[]),
                    Mock(chunks_created=5, document_id="doc456", errors=[]),
                ]
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_deep(
                ctx,
                start_url=start_url,
                max_depth=max_depth,
                allowed_domains=None,
                allowed_subdomains=None,
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Assert
            assert result["success"] is True
            # Verify depth limit was applied
            call_args = mock_crawl.call_args
            assert call_args[1]["max_depth"] == max_depth


@pytest.mark.asyncio
async def test_deep_crawl_error_handling(mock_crawl4ai_deps):
    """Test error handling during deep crawl."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"

    # Mock crawler error
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.side_effect = Exception("Crawl error")

        # Execute
        result = await crawl_and_ingest_deep(
            ctx,
            start_url=start_url,
            max_depth=2,
            allowed_domains=None,
            allowed_subdomains=None,
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Assert
        assert result["success"] is False
        assert result["pages_crawled"] == 0
        assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_deep_crawl_partial_success(mock_crawl4ai_deps):
    """Test deep crawl with partial success (some pages fail)."""
    # Setup
    ctx = MockRunContext(mock_crawl4ai_deps)
    start_url = "https://example.com"

    # Mock crawl results
    crawl_results = [
        {"url": "https://example.com", "markdown": "# Page 1", "metadata": {"title": "Page 1"}},
        {
            "url": "https://example.com/page2",
            "markdown": "# Page 2",
            "metadata": {"title": "Page 2"},
        },
    ]

    # Mock crawler
    with patch(
        "server.projects.crawl4ai_rag.tools.crawl_deep", new_callable=AsyncMock
    ) as mock_crawl:
        mock_crawl.return_value = crawl_results

        # Mock ingestion with one success, one failure
        with patch(
            "server.projects.crawl4ai_rag.tools.CrawledContentIngester"
        ) as mock_ingester_class:
            from server.projects.mongo_rag.ingestion.pipeline import IngestionResult

            mock_ingester = AsyncMock()
            mock_ingester.initialize = AsyncMock()
            # ingest_crawled_batch returns a list of IngestionResult objects
            # One succeeds, one fails
            mock_ingester.ingest_crawled_batch = AsyncMock(
                return_value=[
                    IngestionResult(
                        document_id="doc1",
                        title="Page 1",
                        chunks_created=5,
                        processing_time_ms=100.0,
                        errors=[],
                    ),
                    IngestionResult(
                        document_id="",
                        title="Page 2",
                        chunks_created=0,
                        processing_time_ms=50.0,
                        errors=["Ingestion failed"],
                    ),
                ]
            )
            mock_ingester_class.return_value = mock_ingester

            # Execute
            result = await crawl_and_ingest_deep(
                ctx,
                start_url=start_url,
                max_depth=2,
                allowed_domains=None,
                allowed_subdomains=None,
                chunk_size=1000,
                chunk_overlap=200,
            )

            # Assert - should have partial success
            assert result["pages_crawled"] == len(crawl_results)
            # May have errors but still report pages crawled
            assert result["chunks_created"] > 0 or len(result["errors"]) > 0
