"""Adapter to bridge crawled content with MongoDB RAG ingestion pipeline.

.. deprecated:: 2026-01
    This module is deprecated. Use the centralized ContentIngestionService instead:

    from capabilities.retrieval.mongo_rag.ingestion.content_service import ContentIngestionService

    service = ContentIngestionService()
    await service.initialize()
    result = await service.ingest_content(
        content=markdown,
        title=title,
        source=url,
        source_type="web",
        metadata=metadata,
    )
    await service.close()

    Or use the /api/v1/rag/ingest/content endpoint directly.

    The CrawledContentIngester class is kept for backward compatibility but will
    be removed in a future version.
"""

import asyncio
import logging
import warnings
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from capabilities.retrieval.graphiti_rag.config import config as graphiti_config
from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from capabilities.retrieval.graphiti_rag.ingestion.adapter import GraphitiIngestionAdapter
from capabilities.retrieval.mongo_rag.ingestion.chunker import (
    ChunkingConfig,
    DocumentChunk,
    create_chunker,
)
from capabilities.retrieval.mongo_rag.ingestion.embedder import create_embedder
from capabilities.retrieval.mongo_rag.ingestion.pipeline import IngestionResult
from pymongo import AsyncMongoClient
from workflows.ingestion.crawl4ai_rag.config import config

logger = logging.getLogger(__name__)


class CrawledContentIngester:
    """
    Ingests crawled web content into MongoDB using existing RAG pipeline.

    .. deprecated:: 2026-01
        Use ContentIngestionService from capabilities.retrieval.mongo_rag.ingestion.content_service
        instead. This class is kept for backward compatibility but will be removed.

    This adapter converts crawled markdown content into the format expected
    by the MongoDB RAG ingestion pipeline, reusing chunking and embedding logic.
    """

    def __init__(
        self, mongo_client: AsyncMongoClient, chunk_size: int = 1000, chunk_overlap: int = 200
    ):
        """
        Initialize ingester.

        Args:
            mongo_client: MongoDB client
            chunk_size: Chunk size for document splitting
            chunk_overlap: Chunk overlap size
        """
        warnings.warn(
            "CrawledContentIngester is deprecated. Use ContentIngestionService from "
            "server.projects.mongo_rag.ingestion.content_service instead, or use the "
            "/api/v1/rag/ingest/content endpoint.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.mongo_client = mongo_client
        self.db = mongo_client[config.mongodb_database]

        # Initialize chunker and embedder (reuse from mongo_rag)
        chunker_config = ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_chunk_size=chunk_size * 2,
            max_tokens=512,
        )
        self.chunker = create_chunker(chunker_config)
        self.embedder = create_embedder()

        # Graphiti ingestion adapter (optional)
        self.graphiti_adapter: GraphitiIngestionAdapter | None = None
        self.graphiti_deps: GraphitiRAGDeps | None = None
        self._graphiti_initialized = False

    async def initialize(self) -> None:
        """
        Initialize Graphiti integration.

        Graphiti is enabled by default for crawl4ai RAG flow to automatically
        extract entities and relationships from crawled content. This can be
        disabled by setting USE_GRAPHITI=false in environment variables.

        This method should be called before ingesting documents to ensure
        Graphiti is properly initialized.
        """
        if self._graphiti_initialized:
            return

        # Initialize Graphiti if enabled (enabled by default)
        if graphiti_config.use_graphiti:
            try:
                logger.info("Initializing Graphiti for crawl4ai-rag (enabled by default)")
                self.graphiti_deps = GraphitiRAGDeps.from_settings()
                await self.graphiti_deps.initialize()
                if self.graphiti_deps.graphiti:
                    self.graphiti_adapter = GraphitiIngestionAdapter(self.graphiti_deps.graphiti)
                    logger.info("Graphiti ingestion adapter initialized for crawl4ai-rag")
                else:
                    logger.warning("Graphiti enabled but client not available")
            except Exception as e:
                logger.warning(f"Failed to initialize Graphiti: {e}")
                logger.info("Continuing without Graphiti ingestion")
        else:
            logger.info("Graphiti disabled via USE_GRAPHITI=false")

        self._graphiti_initialized = True

    def _extract_title(self, url: str, markdown: str) -> str:
        """
        Extract title from markdown or use URL.

        Args:
            url: Source URL
            markdown: Markdown content

        Returns:
            Document title
        """
        # Try to find markdown title
        lines = markdown.split("\n")
        for raw_line in lines[:10]:  # Check first 10 lines
            line = raw_line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fallback to URL path
        parsed = urlparse(url)
        if parsed.path and parsed.path != "/":
            # Use last part of path
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                return path_parts[-1].replace("-", " ").replace("_", " ")

        # Final fallback: use domain
        return parsed.netloc or url

    def _extract_metadata(
        self, url: str, markdown: str, crawl_metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Extract metadata from crawled content and merge with crawl metadata.

        Args:
            url: Source URL
            markdown: Markdown content
            crawl_metadata: Optional metadata from crawl4ai result

        Returns:
            Metadata dictionary
        """
        parsed = urlparse(url)

        # Base metadata
        metadata = {
            "url": url,
            "domain": parsed.netloc,
            "path": parsed.path,
            "source_type": "web_crawl",
            "crawl_date": datetime.now().isoformat(),
            "file_size": len(markdown),
            "line_count": len(markdown.split("\n")),
            "word_count": len(markdown.split()),
        }

        # Merge crawl metadata if provided
        if crawl_metadata:
            # Page metadata
            if "page_title" in crawl_metadata:
                metadata["page_title"] = crawl_metadata["page_title"]
            if "page_description" in crawl_metadata:
                metadata["page_description"] = crawl_metadata["page_description"]
            if "page_language" in crawl_metadata:
                metadata["page_language"] = crawl_metadata["page_language"]
            if "page_keywords" in crawl_metadata:
                metadata["page_keywords"] = crawl_metadata["page_keywords"]
            if "page_author" in crawl_metadata:
                metadata["page_author"] = crawl_metadata["page_author"]

            # Open Graph metadata
            if "og_title" in crawl_metadata:
                metadata["og_title"] = crawl_metadata["og_title"]
            if "og_description" in crawl_metadata:
                metadata["og_description"] = crawl_metadata["og_description"]
            if "og_image" in crawl_metadata:
                metadata["og_image"] = crawl_metadata["og_image"]

            # Content metadata
            if "images" in crawl_metadata:
                metadata["images"] = crawl_metadata["images"]
            if "image_count" in crawl_metadata:
                metadata["image_count"] = crawl_metadata["image_count"]
            if "media" in crawl_metadata:
                metadata["media"] = crawl_metadata["media"]
            if "media_count" in crawl_metadata:
                metadata["media_count"] = crawl_metadata["media_count"]
            if "structured_data" in crawl_metadata:
                metadata["structured_data"] = crawl_metadata["structured_data"]

            # Link metadata
            if "link_counts" in crawl_metadata:
                metadata["link_counts"] = crawl_metadata["link_counts"]

            # Crawl metadata
            if "crawl_depth" in crawl_metadata:
                metadata["crawl_depth"] = crawl_metadata["crawl_depth"]
            if "parent_url" in crawl_metadata:
                metadata["parent_url"] = crawl_metadata["parent_url"]
            if "crawl_timestamp" in crawl_metadata:
                metadata["crawl_timestamp"] = crawl_metadata["crawl_timestamp"]

        return metadata

    async def ingest_crawled_page(
        self,
        url: str,
        markdown: str,
        html: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        crawl_metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """
        Ingest a single crawled page.

        Args:
            url: Source URL
            markdown: Markdown content from crawl
            chunk_size: Override chunk size (optional)
            chunk_overlap: Override chunk overlap (optional)
            crawl_metadata: Optional metadata from crawl4ai result

        Returns:
            IngestionResult with document ID and stats
        """
        from datetime import datetime

        start_time = datetime.now()

        try:
            # Extract title - prefer page title from metadata if available
            if crawl_metadata and "page_title" in crawl_metadata:
                title = crawl_metadata["page_title"]
            else:
                title = self._extract_title(url, markdown)

            # Extract and merge metadata
            metadata = self._extract_metadata(url, markdown, crawl_metadata)

            # Update chunker config if overrides provided
            if chunk_size is not None or chunk_overlap is not None:
                chunker_config = ChunkingConfig(
                    chunk_size=chunk_size or config.default_chunk_size,
                    chunk_overlap=chunk_overlap or config.default_chunk_overlap,
                    max_chunk_size=(chunk_size or config.default_chunk_size) * 2,
                    max_tokens=512,
                )
                chunker = create_chunker(chunker_config)
            else:
                chunker = self.chunker

            # Chunk the document (no DoclingDocument for markdown, will use fallback)
            chunks = await chunker.chunk_document(
                content=markdown,
                title=title,
                source=url,
                metadata=metadata,
                docling_doc=None,  # Crawled content is already markdown
            )

            if not chunks:
                logger.warning(f"No chunks created for {url}")
                return IngestionResult(
                    document_id="",
                    title=title,
                    chunks_created=0,
                    processing_time_ms=0,
                    errors=["No chunks created"],
                )

            logger.info(f"Created {len(chunks)} chunks for {url}")

            # Generate embeddings
            embedded_chunks = await self.embedder.embed_chunks(chunks)
            logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

            # Save to MongoDB (include HTML in metadata if available)
            if html:
                metadata["original_html"] = html

            # Save to MongoDB
            document_id = await self._save_to_mongodb(
                title=title, source=url, content=markdown, chunks=embedded_chunks, metadata=metadata
            )

            logger.info(f"Saved document to MongoDB with ID: {document_id}")

            # Ingest into Graphiti if enabled
            graphiti_errors = []
            if self.graphiti_adapter:
                try:
                    graphiti_result = await self.graphiti_adapter.ingest_document(
                        document_id=document_id,
                        chunks=embedded_chunks,
                        metadata=metadata,
                        title=title,
                        source=url,
                    )
                    if graphiti_result.get("errors"):
                        graphiti_errors.extend(graphiti_result["errors"])
                    logger.info(
                        f"Graphiti ingestion: {graphiti_result.get('facts_added', 0)} facts "
                        f"from {graphiti_result.get('chunks_processed', 0)} chunks"
                    )
                except Exception as e:
                    error_msg = f"Graphiti ingestion failed: {e!s}"
                    logger.exception(error_msg)
                    graphiti_errors.append(error_msg)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return IngestionResult(
                document_id=document_id,
                title=title,
                chunks_created=len(chunks),
                processing_time_ms=processing_time,
                errors=graphiti_errors,
            )

        except Exception as e:
            logger.exception("Error ingesting {url}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return IngestionResult(
                document_id="",
                title=url,
                chunks_created=0,
                processing_time_ms=processing_time,
                errors=[str(e)],
            )

    async def ingest_crawled_batch(
        self,
        pages: list[dict[str, Any]],
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        max_concurrent: int = 5,
    ) -> list[IngestionResult]:
        """
        Ingest multiple crawled pages in parallel.

        Args:
            pages: List of dictionaries with 'url', 'markdown', and optional 'metadata' keys
            chunk_size: Override chunk size (optional)
            chunk_overlap: Override chunk overlap (optional)
            max_concurrent: Maximum concurrent ingestion tasks (default: 5)

        Returns:
            List of IngestionResult objects
        """
        # Filter out invalid pages
        valid_pages = []
        for page in pages:
            url = page.get("url")
            markdown = page.get("markdown", "")
            if url and markdown:
                valid_pages.append(page)
            else:
                logger.warning(f"Skipping invalid page: {url}")

        if not valid_pages:
            logger.warning("No valid pages to ingest")
            return []

        logger.info(
            f"Starting parallel ingestion of {len(valid_pages)} pages (max_concurrent={max_concurrent})"
        )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def ingest_with_semaphore(page: dict[str, Any]) -> IngestionResult:
            """Ingest a single page with semaphore control."""
            async with semaphore:
                url = page.get("url")
                markdown = page.get("markdown", "")
                html = page.get("html")  # Get HTML content
                crawl_metadata = page.get("metadata")

                return await self.ingest_crawled_page(
                    url=url,
                    markdown=markdown,
                    html=html,  # Pass HTML content
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    crawl_metadata=crawl_metadata,
                )

        # Process all pages in parallel with concurrency limit
        results = await asyncio.gather(
            *[ingest_with_semaphore(page) for page in valid_pages], return_exceptions=True
        )

        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error ingesting page {valid_pages[i].get('url')}: {result}")
                processed_results.append(
                    IngestionResult(
                        document_id="",
                        title=valid_pages[i].get("url", "unknown"),
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(result)],
                    )
                )
            else:
                processed_results.append(result)

        logger.info(f"Completed parallel ingestion: {len(processed_results)} pages processed")
        return processed_results

    async def _save_to_mongodb(
        self,
        title: str,
        source: str,
        content: str,
        chunks: list[DocumentChunk],
        metadata: dict[str, Any],
    ) -> str:
        """
        Save document and chunks to MongoDB.

        Args:
            title: Document title
            source: Document source URL
            content: Document content
            chunks: List of document chunks with embeddings
            metadata: Document metadata

        Returns:
            Document ID (ObjectId as string)
        """
        documents_collection = self.db[config.mongodb_collection_documents]
        chunks_collection = self.db[config.mongodb_collection_chunks]

        # Insert document
        document_dict = {
            "title": title,
            "source": source,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now(),
        }

        document_result = await documents_collection.insert_one(document_dict)
        document_id = document_result.inserted_id

        logger.info(f"Inserted document with ID: {document_id}")

        # Insert chunks with embeddings
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "document_id": document_id,
                "content": chunk.content,
                "embedding": chunk.embedding,  # Python list
                "chunk_index": chunk.index,
                "metadata": chunk.metadata,
                "token_count": chunk.token_count,
                "created_at": datetime.now(),
            }
            chunk_dicts.append(chunk_dict)

        # Batch insert
        if chunk_dicts:
            await chunks_collection.insert_many(chunk_dicts, ordered=False)
            logger.info(f"Inserted {len(chunk_dicts)} chunks")

        return str(document_id)
