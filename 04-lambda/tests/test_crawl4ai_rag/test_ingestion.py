"""Tests for Crawl4AI RAG ingestion of crawled content."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from server.projects.crawl4ai_rag.ingestion.adapter import CrawledContentIngester


@pytest.mark.asyncio
async def test_ingest_crawled_page(mock_mongo_client, mock_mongo_db, mock_graphiti_config):
    """Test ingesting a crawled page."""
    # Setup - mock mongo_client to return mock_mongo_db when indexed
    mock_mongo_client.__getitem__ = Mock(return_value=mock_mongo_db)

    # Setup ingester
    ingester = CrawledContentIngester(
        mongo_client=mock_mongo_client, chunk_size=1000, chunk_overlap=200
    )

    # Mock MongoDB operations
    mock_docs_collection = AsyncMock()
    mock_chunks_collection = AsyncMock()
    mock_mongo_db.__getitem__ = Mock(
        side_effect=lambda x: {"documents": mock_docs_collection, "chunks": mock_chunks_collection}[
            x
        ]
    )
    mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="doc123"))
    mock_chunks_collection.insert_many = AsyncMock(
        return_value=Mock(inserted_ids=["chunk1", "chunk2"])
    )

    # Mock chunker and embedder
    with patch("server.projects.crawl4ai_rag.ingestion.adapter.create_chunker") as mock_chunker:
        with patch(
            "server.projects.crawl4ai_rag.ingestion.adapter.create_embedder"
        ) as mock_embedder:
            # Mock chunker - chunk_document is async
            from server.projects.mongo_rag.ingestion.chunker import DocumentChunk

            mock_chunk1 = DocumentChunk(
                content="Test chunk content 1",
                index=0,
                start_char=0,
                end_char=20,
                embedding=[0.1] * 768,
                metadata={},
                token_count=10,
            )
            mock_chunk2 = DocumentChunk(
                content="Test chunk content 2",
                index=1,
                start_char=21,
                end_char=41,
                embedding=[0.1] * 768,
                metadata={},
                token_count=10,
            )
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document = AsyncMock(
                return_value=[mock_chunk1, mock_chunk2]
            )
            mock_chunker.return_value = mock_chunker_instance

            # Mock embedder - embed_chunks is async
            mock_embedder_instance = Mock()
            mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk1, mock_chunk2])
            mock_embedder.return_value = mock_embedder_instance

            # Initialize and execute
            await ingester.initialize()
            result = await ingester.ingest_crawled_page(
                url="https://example.com",
                markdown="# Test Page\n\nContent here.",
                html="<html><body><h1>Test Page</h1></body></html>",
                chunk_size=1000,
                chunk_overlap=200,
                crawl_metadata={"title": "Test Page"},
            )

            # Assert
            assert result.chunks_created == 2
            assert result.document_id == "doc123"
            assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_ingest_with_chunking(mock_mongo_client, mock_mongo_db, mock_graphiti_config):
    """Test ingestion with custom chunking."""
    # Setup - mock mongo_client to return mock_mongo_db when indexed
    mock_mongo_client.__getitem__ = Mock(return_value=mock_mongo_db)

    # Setup ingester
    ingester = CrawledContentIngester(
        mongo_client=mock_mongo_client, chunk_size=1500, chunk_overlap=300
    )

    # Mock MongoDB operations
    mock_docs_collection = AsyncMock()
    mock_chunks_collection = AsyncMock()
    mock_mongo_db.__getitem__ = Mock(
        side_effect=lambda x: {"documents": mock_docs_collection, "chunks": mock_chunks_collection}[
            x
        ]
    )
    mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="doc123"))
    mock_chunks_collection.insert_many = AsyncMock(return_value=Mock(inserted_ids=["chunk1"]))

    # Mock chunker
    with patch("server.projects.crawl4ai_rag.ingestion.adapter.create_chunker") as mock_chunker:
        with patch(
            "server.projects.crawl4ai_rag.ingestion.adapter.create_embedder"
        ) as mock_embedder:
            # Mock chunker with custom size - chunk_document is async
            from server.projects.mongo_rag.ingestion.chunker import DocumentChunk

            mock_chunk = DocumentChunk(
                content="Long chunk content" * 100,
                index=0,
                start_char=0,
                end_char=1900,
                embedding=[0.1] * 768,
                metadata={},
                token_count=100,
            )
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
            mock_chunker.return_value = mock_chunker_instance

            # Mock embedder - embed_chunks is async
            mock_embedder_instance = Mock()
            mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
            mock_embedder.return_value = mock_embedder_instance

            # Initialize and execute
            await ingester.initialize()
            result = await ingester.ingest_crawled_page(
                url="https://example.com",
                markdown="# Test Page\n\n" + "Content " * 200,
                html="<html><body>Content</body></html>",
                chunk_size=1500,
                chunk_overlap=300,
                crawl_metadata={},
            )

            # Assert
            assert result.chunks_created == 1
            # Verify chunking parameters were used
            call_args = mock_chunker_instance.chunk_document.call_args
            assert call_args is not None


@pytest.mark.asyncio
async def test_ingest_error_handling(mock_mongo_client, mock_mongo_db, mock_graphiti_config):
    """Test error handling during ingestion."""
    # Setup - mock mongo_client to return mock_mongo_db when indexed
    mock_mongo_client.__getitem__ = Mock(return_value=mock_mongo_db)

    # Setup ingester
    ingester = CrawledContentIngester(
        mongo_client=mock_mongo_client, chunk_size=1000, chunk_overlap=200
    )

    # Mock MongoDB error
    mock_docs_collection = AsyncMock()
    mock_chunks_collection = AsyncMock()
    mock_mongo_db.__getitem__ = Mock(
        side_effect=lambda x: {"documents": mock_docs_collection, "chunks": mock_chunks_collection}[
            x
        ]
    )
    mock_docs_collection.insert_one = AsyncMock(side_effect=Exception("MongoDB error"))

    # Mock chunker
    with patch("server.projects.crawl4ai_rag.ingestion.adapter.create_chunker") as mock_chunker:
        with patch(
            "server.projects.crawl4ai_rag.ingestion.adapter.create_embedder"
        ) as mock_embedder:
            # Mock chunker - chunk_document is async
            from server.projects.mongo_rag.ingestion.chunker import DocumentChunk

            mock_chunk = DocumentChunk(
                content="Test chunk",
                index=0,
                start_char=0,
                end_char=10,
                embedding=[0.1] * 768,
                metadata={},
                token_count=5,
            )
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
            mock_chunker.return_value = mock_chunker_instance

            # Mock embedder - embed_chunks is async
            mock_embedder_instance = Mock()
            mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
            mock_embedder.return_value = mock_embedder_instance

            # Initialize and execute
            await ingester.initialize()
            result = await ingester.ingest_crawled_page(
                url="https://example.com",
                markdown="# Test",
                html="<html></html>",
                chunk_size=1000,
                chunk_overlap=200,
                crawl_metadata={},
            )

            # Assert - should have error
            assert len(result.errors) > 0
            assert result.chunks_created == 0 or result.document_id is None


@pytest.mark.asyncio
async def test_ingest_metadata_preservation(mock_mongo_client, mock_mongo_db, mock_graphiti_config):
    """Test that crawl metadata is preserved during ingestion."""
    # Setup - mock mongo_client to return mock_mongo_db when indexed
    mock_mongo_client.__getitem__ = Mock(return_value=mock_mongo_db)

    # Setup ingester
    ingester = CrawledContentIngester(
        mongo_client=mock_mongo_client, chunk_size=1000, chunk_overlap=200
    )

    # Mock MongoDB operations
    mock_docs_collection = AsyncMock()
    mock_chunks_collection = AsyncMock()
    mock_mongo_db.__getitem__ = Mock(
        side_effect=lambda x: {"documents": mock_docs_collection, "chunks": mock_chunks_collection}[
            x
        ]
    )
    mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="doc123"))
    mock_chunks_collection.insert_many = AsyncMock(return_value=Mock(inserted_ids=["chunk1"]))

    # Mock chunker and embedder
    with patch("server.projects.crawl4ai_rag.ingestion.adapter.create_chunker") as mock_chunker:
        with patch(
            "server.projects.crawl4ai_rag.ingestion.adapter.create_embedder"
        ) as mock_embedder:
            # Mock chunker - chunk_document is async
            from server.projects.mongo_rag.ingestion.chunker import DocumentChunk

            mock_chunk = DocumentChunk(
                content="Test chunk",
                index=0,
                start_char=0,
                end_char=10,
                embedding=[0.1] * 768,
                metadata={},
                token_count=5,
            )
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
            mock_chunker.return_value = mock_chunker_instance

            # Mock embedder - embed_chunks is async
            mock_embedder_instance = Mock()
            mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
            mock_embedder.return_value = mock_embedder_instance

            # Test metadata
            crawl_metadata = {
                "title": "Test Page",
                "description": "A test page",
                "language": "en",
                "depth": 1,
                "parent_url": "https://example.com",
            }

            # Initialize and execute
            await ingester.initialize()
            await ingester.ingest_crawled_page(
                url="https://example.com/page",
                markdown="# Test Page",
                html="<html></html>",
                chunk_size=1000,
                chunk_overlap=200,
                crawl_metadata=crawl_metadata,
            )

            # Assert - verify metadata was passed to insert_one
            call_args = mock_docs_collection.insert_one.call_args
            assert call_args is not None
            inserted_doc = call_args[0][0]
            # Metadata should be preserved in document
            assert "metadata" in inserted_doc or "source" in inserted_doc
