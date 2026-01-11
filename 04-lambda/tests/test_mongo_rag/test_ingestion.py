"""Tests for MongoDB RAG document ingestion."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
from bson import ObjectId

from server.projects.mongo_rag.ingestion.pipeline import (
    DocumentIngestionPipeline,
    IngestionConfig,
    IngestionResult
)


@pytest.mark.asyncio
async def test_ingest_pdf(mock_mongo_client, mock_mongo_db, mock_ingestion_settings):
    """Test PDF document ingestion."""
    # Setup
    config = IngestionConfig(chunk_size=1000, chunk_overlap=200)
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="/tmp/test_docs",
        clean_before_ingest=False
    )
    pipeline.settings = mock_ingestion_settings
    pipeline.mongo_client = mock_mongo_client
    pipeline.db = mock_mongo_db
    pipeline._initialized = True  # Skip initialization
    
    # Mock file operations
    with patch("os.path.exists", return_value=True):
        with patch.object(pipeline, "_find_document_files", return_value=["/tmp/test_docs/test.pdf"]):
            with patch.object(pipeline, "_read_document", return_value=("PDF content", None)):
                with patch("server.projects.mongo_rag.ingestion.pipeline.create_chunker") as mock_chunker:
                    with patch("server.projects.mongo_rag.ingestion.pipeline.create_embedder") as mock_embedder:
                        # Mock chunker
                        mock_chunk = Mock()
                        mock_chunk.text = "Test chunk content"
                        mock_chunk.content = "Test chunk content"
                        mock_chunker_instance = Mock()
                        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
                        mock_chunker.return_value = mock_chunker_instance
                        pipeline.chunker = mock_chunker_instance
                        
                        # Mock embedder
                        mock_embedder_instance = Mock()
                        mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
                        mock_embedder.return_value = mock_embedder_instance
                        pipeline.embedder = mock_embedder_instance
                        
                        # Mock MongoDB operations
                        mock_docs_collection = AsyncMock()
                        mock_chunks_collection = AsyncMock()
                        mock_mongo_db.__getitem__ = Mock(side_effect=lambda x: {
                            mock_ingestion_settings.mongodb_collection_documents: mock_docs_collection,
                            mock_ingestion_settings.mongodb_collection_chunks: mock_chunks_collection
                        }[x])
                        mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=ObjectId()))
                        mock_chunks_collection.insert_many = AsyncMock()
                        
                        # Execute (skip initialize since we've already set up mocks)
                        results = await pipeline.ingest_documents()
                        
                        # Assert
                        assert len(results) > 0
                        assert results[0].chunks_created > 0


@pytest.mark.asyncio
async def test_ingest_markdown(mock_mongo_client, mock_mongo_db, mock_ingestion_settings):
    """Test markdown document ingestion."""
    # Setup
    config = IngestionConfig(chunk_size=1000, chunk_overlap=200)
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="/tmp/test_docs",
        clean_before_ingest=False
    )
    pipeline.settings = mock_ingestion_settings
    pipeline.mongo_client = mock_mongo_client
    pipeline.db = mock_mongo_db
    pipeline._initialized = True  # Skip initialization
    
    # Mock file operations
    with patch("os.path.exists", return_value=True):
        with patch.object(pipeline, "_find_document_files", return_value=["/tmp/test_docs/test.md"]):
            with patch.object(pipeline, "_read_document", return_value=("# Test\n\nContent here.", None)):
                with patch("server.projects.mongo_rag.ingestion.pipeline.create_chunker") as mock_chunker:
                    with patch("server.projects.mongo_rag.ingestion.pipeline.create_embedder") as mock_embedder:
                        # Mock chunker
                        mock_chunk = Mock()
                        mock_chunk.text = "# Test\n\nContent here."
                        mock_chunk.content = "# Test\n\nContent here."
                        mock_chunker_instance = Mock()
                        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
                        mock_chunker.return_value = mock_chunker_instance
                        pipeline.chunker = mock_chunker_instance
                        
                        # Mock embedder
                        mock_embedder_instance = Mock()
                        mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
                        mock_embedder.return_value = mock_embedder_instance
                        pipeline.embedder = mock_embedder_instance
                        
                        # Mock MongoDB operations
                        mock_docs_collection = AsyncMock()
                        mock_chunks_collection = AsyncMock()
                        mock_mongo_db.__getitem__ = Mock(side_effect=lambda x: {
                            mock_ingestion_settings.mongodb_collection_documents: mock_docs_collection,
                            mock_ingestion_settings.mongodb_collection_chunks: mock_chunks_collection
                        }[x])
                        mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=ObjectId()))
                        mock_chunks_collection.insert_many = AsyncMock()
                        
                        # Execute (skip initialize since we've already set up mocks)
                        results = await pipeline.ingest_documents()
                        
                        # Assert
                        assert len(results) > 0


@pytest.mark.asyncio
async def test_ingest_multiple_files(mock_mongo_client, mock_mongo_db, mock_ingestion_settings):
    """Test batch ingestion of multiple files."""
    # Setup
    config = IngestionConfig(chunk_size=1000, chunk_overlap=200)
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="/tmp/test_docs",
        clean_before_ingest=False
    )
    pipeline.settings = mock_ingestion_settings
    pipeline.mongo_client = mock_mongo_client
    pipeline.db = mock_mongo_db
    pipeline._initialized = True  # Skip initialization
    
    # Mock multiple files
    files = ["/tmp/test_docs/doc1.pdf", "/tmp/test_docs/doc2.pdf", "/tmp/test_docs/doc3.md"]
    with patch("os.path.exists", return_value=True):
        with patch.object(pipeline, "_find_document_files", return_value=files):
            with patch.object(pipeline, "_read_document", return_value=("Content", None)):
                with patch("server.projects.mongo_rag.ingestion.pipeline.create_chunker") as mock_chunker:
                    with patch("server.projects.mongo_rag.ingestion.pipeline.create_embedder") as mock_embedder:
                        # Mock chunker
                        mock_chunk = Mock()
                        mock_chunk.text = "Content"
                        mock_chunk.content = "Content"
                        mock_chunker_instance = Mock()
                        mock_chunker_instance.chunk_document = AsyncMock(return_value=[mock_chunk])
                        mock_chunker.return_value = mock_chunker_instance
                        pipeline.chunker = mock_chunker_instance
                        
                        # Mock embedder
                        mock_embedder_instance = Mock()
                        mock_embedder_instance.embed_chunks = AsyncMock(return_value=[mock_chunk])
                        mock_embedder.return_value = mock_embedder_instance
                        pipeline.embedder = mock_embedder_instance
                        
                        # Mock MongoDB operations
                        mock_docs_collection = AsyncMock()
                        mock_chunks_collection = AsyncMock()
                        mock_mongo_db.__getitem__ = Mock(side_effect=lambda x: {
                            mock_ingestion_settings.mongodb_collection_documents: mock_docs_collection,
                            mock_ingestion_settings.mongodb_collection_chunks: mock_chunks_collection
                        }[x])
                        mock_docs_collection.insert_one = AsyncMock(return_value=Mock(inserted_id=ObjectId()))
                        mock_chunks_collection.insert_many = AsyncMock()
                        
                        # Execute (skip initialize since we've already set up mocks)
                        results = await pipeline.ingest_documents()
                        
                        # Assert
                        assert len(results) == len(files)


@pytest.mark.asyncio
async def test_ingest_clean_before(mock_mongo_client, mock_mongo_db, mock_ingestion_settings):
    """Test clean before ingestion."""
    # Setup
    config = IngestionConfig(chunk_size=1000, chunk_overlap=200)
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="/tmp/test_docs",
        clean_before_ingest=True
    )
    pipeline.settings = mock_ingestion_settings
    pipeline.mongo_client = mock_mongo_client
    pipeline.db = mock_mongo_db
    pipeline._initialized = True  # Skip initialization
    
    # Mock MongoDB collections
    mock_docs_collection = AsyncMock()
    mock_chunks_collection = AsyncMock()
    mock_mongo_db.__getitem__ = Mock(side_effect=lambda x: {
        mock_ingestion_settings.mongodb_collection_documents: mock_docs_collection,
        mock_ingestion_settings.mongodb_collection_chunks: mock_chunks_collection
    }[x])
    
    # Mock delete operations
    mock_docs_collection.delete_many = AsyncMock()
    mock_chunks_collection.delete_many = AsyncMock()
    
    # Call clean method directly
    await pipeline._clean_databases()
    
    # Assert - verify delete was called
    mock_docs_collection.delete_many.assert_called_once()
    mock_chunks_collection.delete_many.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_error_handling(mock_mongo_client, mock_mongo_db, mock_ingestion_settings):
    """Test error handling during ingestion."""
    # Setup
    config = IngestionConfig(chunk_size=1000, chunk_overlap=200)
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="/tmp/test_docs",
        clean_before_ingest=False
    )
    pipeline.settings = mock_ingestion_settings
    pipeline.mongo_client = mock_mongo_client
    pipeline.db = mock_mongo_db
    pipeline._initialized = True  # Skip initialization
    
    # Mock file that causes error
    with patch("os.path.exists", return_value=True):
        with patch.object(pipeline, "_find_document_files", return_value=["/tmp/test_docs/invalid.pdf"]):
            with patch.object(pipeline, "_read_document", side_effect=Exception("File read error")):
                # Execute (skip initialize since we've already set up mocks)
                results = await pipeline.ingest_documents()
                
                # Assert - should have error in results
                assert len(results) > 0
                assert len(results[0].errors) > 0
