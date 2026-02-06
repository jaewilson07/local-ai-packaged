"""
Centralized content ingestion service for MongoDB RAG.

This service provides a single entry point for ingesting any content (markdown, text,
web pages, YouTube transcripts, etc.) into the MongoDB RAG knowledge base.

Benefits:
- Consistent RLS fields on all documents
- Proper Docling integration for structure-aware chunking
- Centralized Graphiti ingestion
- Single place to maintain ingestion logic
"""

import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pymongo import AsyncMongoClient

if TYPE_CHECKING:
    from capabilities.retrieval.graphiti_rag.ingestion.adapter import (
        GraphitiIngestionOptions,
    )

    from app.core.models import IngestionOptions, ScrapedContent
from app.capabilities.retrieval.graphiti_rag.config import config as graphiti_config
from app.capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from app.capabilities.retrieval.graphiti_rag.ingestion.adapter import GraphitiIngestionAdapter
from app.capabilities.retrieval.mongo_rag.config import config as rag_config
from app.capabilities.retrieval.mongo_rag.extraction.code_ingestion import ingest_code_examples
from app.capabilities.retrieval.mongo_rag.ingestion.chunker import (
    ChunkingConfig,
    DocumentChunk,
    create_chunker,
)
from app.capabilities.retrieval.mongo_rag.ingestion.embedder import create_embedder
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ContentIngestionResult:
    """Result of content ingestion."""

    document_id: str
    title: str
    source: str
    source_type: str
    chunks_created: int
    processing_time_ms: float
    errors: list[str]


class ContentIngestionService:
    """
    Centralized service for ingesting any content into MongoDB RAG.

    This service:
    - Accepts markdown/text content directly (no file uploads needed)
    - Optionally parses through Docling for structure-aware chunking
    - Applies RLS fields consistently
    - Handles Graphiti ingestion centrally
    - Extracts code examples when enabled

    Usage:
        service = ContentIngestionService()
        await service.initialize()
        try:
            result = await service.ingest_content(
                content="# My Document\\n...",
                title="My Document",
                source="https://example.com/doc",
                source_type="web",
                metadata={"domain": "example.com"},
                user_email="user@example.com",
            )
        finally:
            await service.close()
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_tokens: int = 512,
    ):
        """
        Initialize content ingestion service.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            max_tokens: Maximum tokens per chunk for embedding models
        """
        self.settings = rag_config

        # Initialize MongoDB client (will be set in initialize())
        self.mongo_client: AsyncMongoClient | None = None
        self.db: Any | None = None

        # Initialize chunker and embedder
        self.chunker_config = ChunkingConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_chunk_size=chunk_size * 2,
            max_tokens=max_tokens,
        )
        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()

        # Graphiti adapter (optional)
        self.graphiti_adapter: GraphitiIngestionAdapter | None = None
        self.graphiti_deps: GraphitiRAGDeps | None = None

        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize MongoDB and Graphiti connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        if self._initialized:
            return

        logger.info("Initializing ContentIngestionService...")

        try:
            # Initialize MongoDB client
            self.mongo_client = AsyncMongoClient(
                self.settings.mongodb_uri, serverSelectionTimeoutMS=5000
            )
            self.db = self.mongo_client[self.settings.mongodb_database]

            # Verify connection
            await self.mongo_client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {self.settings.mongodb_database}")

            # Initialize Graphiti if enabled
            if graphiti_config.use_graphiti:
                try:
                    self.graphiti_deps = GraphitiRAGDeps.from_settings()
                    await self.graphiti_deps.initialize()
                    if self.graphiti_deps.graphiti:
                        self.graphiti_adapter = GraphitiIngestionAdapter(
                            self.graphiti_deps.graphiti
                        )
                        logger.info("Graphiti ingestion adapter initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize Graphiti: {e}")
                    logger.info("Continuing without Graphiti ingestion")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.exception("mongodb_connection_failed", error=str(e))
            raise

        self._initialized = True
        logger.info("ContentIngestionService initialized")

    async def close(self) -> None:
        """Close MongoDB and Graphiti connections."""
        if self._initialized:
            if self.mongo_client:
                await self.mongo_client.close()
                self.mongo_client = None
                self.db = None
                logger.info("MongoDB connection closed")

            if self.graphiti_deps:
                await self.graphiti_deps.cleanup()
                self.graphiti_adapter = None
                self.graphiti_deps = None

            self._initialized = False

    def _convert_markdown_to_docling(self, content: str) -> Any:
        """
        Convert markdown content to DoclingDocument using Docling's DocumentConverter.

        Args:
            content: Markdown content

        Returns:
            DoclingDocument or None if conversion fails
        """
        try:
            from docling.document_converter import DocumentConverter

            # Write markdown to temp file (Docling needs a file path)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as f:
                f.write(content)
                temp_path = f.name

            try:
                converter = DocumentConverter()
                result = converter.convert(temp_path)
                logger.info("Successfully converted markdown to DoclingDocument")
                return result.document
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.warning(f"Failed to convert markdown to DoclingDocument: {e}")
            return None

    def _extract_title_from_content(self, content: str, default_title: str) -> str:
        """
        Extract title from markdown content.

        Args:
            content: Markdown content
            default_title: Fallback title if not found

        Returns:
            Extracted or default title
        """
        lines = content.split("\n")
        for raw_line in lines[:10]:
            line = raw_line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return default_title

    def _extract_metadata_from_content(self, content: str) -> dict[str, Any]:
        """
        Extract metadata from markdown frontmatter.

        Args:
            content: Markdown content (may include YAML frontmatter)

        Returns:
            Extracted metadata dictionary
        """
        metadata: dict[str, Any] = {}

        if content.startswith("---"):
            try:
                import yaml

                end_marker = content.find("\n---\n", 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict):
                        metadata.update(yaml_metadata)
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")

        return metadata

    async def _save_to_mongodb(
        self,
        title: str,
        source: str,
        source_type: str,
        content: str,
        chunks: list[DocumentChunk],
        metadata: dict[str, Any],
        user_id: str | None = None,
        user_email: str | None = None,
        is_public: bool = False,
    ) -> str:
        """
        Save document and chunks to MongoDB with RLS fields.

        Args:
            title: Document title
            source: Document source (URL or identifier)
            source_type: Type of source (web, youtube, article, custom)
            content: Full document content
            chunks: List of document chunks with embeddings
            metadata: Document metadata
            user_id: User UUID for RLS
            user_email: User email for RLS
            is_public: Whether document is publicly accessible

        Returns:
            Document ID (ObjectId as string)
        """
        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Insert document with RLS fields
        document_dict = {
            "title": title,
            "source": source,
            "source_type": source_type,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now(),
            # RLS fields - always included
            "user_id": user_id,
            "user_email": user_email,
            "is_public": is_public,
            "shared_with": [],
            "group_ids": [],
        }

        document_result = await documents_collection.insert_one(document_dict)
        document_id = document_result.inserted_id

        logger.info(f"Inserted document with ID: {document_id}")

        # Insert chunks with embeddings
        chunk_dicts = []
        for chunk in chunks:
            # Add RLS fields to chunk metadata as well
            chunk_metadata = {
                **chunk.metadata,
                "user_id": user_id,
                "user_email": user_email,
            }

            chunk_dict = {
                "document_id": document_id,
                "content": chunk.content,
                "embedding": chunk.embedding,
                "chunk_index": chunk.index,
                "metadata": chunk_metadata,
                "token_count": chunk.token_count,
                "created_at": datetime.now(),
                # RLS fields on chunks too
                "user_id": user_id,
                "user_email": user_email,
            }
            chunk_dicts.append(chunk_dict)

        # Batch insert
        if chunk_dicts:
            await chunks_collection.insert_many(chunk_dicts, ordered=False)
            logger.info(f"Inserted {len(chunk_dicts)} chunks")

        return str(document_id)

    async def ingest_content(
        self,
        content: str,
        title: str,
        source: str,
        source_type: str,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        user_email: str | None = None,
        is_public: bool = False,
        use_docling: bool = True,
        extract_code_examples: bool = True,
    ) -> ContentIngestionResult:
        """
        Ingest arbitrary content into MongoDB RAG.

        This is the single entry point for all content ingestion. It handles:
        - Markdown parsing via Docling (optional but recommended)
        - Structure-aware chunking via HybridChunker
        - Embedding generation
        - MongoDB storage with proper RLS fields
        - Graphiti knowledge graph ingestion (if enabled)
        - Code example extraction (if enabled)

        Args:
            content: Markdown or plain text content
            title: Document title
            source: Source URL or identifier
            source_type: Type of source ("web", "youtube", "article", "custom")
            metadata: Additional metadata dictionary
            user_id: User UUID for RLS (row-level security)
            user_email: User email for RLS
            is_public: Whether document is publicly accessible
            use_docling: Whether to parse through Docling for better chunking
            extract_code_examples: Whether to extract and index code examples

        Returns:
            ContentIngestionResult with document ID and statistics
        """
        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        errors: list[str] = []

        # Build metadata
        base_metadata = {
            "source_type": source_type,
            "ingested_at": datetime.now().isoformat(),
            **(metadata or {}),
        }

        # Extract frontmatter metadata if present
        frontmatter = self._extract_metadata_from_content(content)
        base_metadata.update(frontmatter)

        # Use provided title or extract from content
        final_title = title or self._extract_title_from_content(content, "Untitled")

        logger.info(f"Ingesting content: {final_title} ({source_type})")

        # Convert to DoclingDocument if requested
        docling_doc = None
        if use_docling:
            docling_doc = self._convert_markdown_to_docling(content)
            if docling_doc:
                base_metadata["docling_converted"] = True

        # Chunk the document
        chunks = await self.chunker.chunk_document(
            content=content,
            title=final_title,
            source=source,
            metadata=base_metadata,
            docling_doc=docling_doc,
        )

        if not chunks:
            return ContentIngestionResult(
                document_id="",
                title=final_title,
                source=source,
                source_type=source_type,
                chunks_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created from content"],
            )

        logger.info(f"Created {len(chunks)} chunks")

        # Generate embeddings
        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        # Save to MongoDB
        document_id = await self._save_to_mongodb(
            title=final_title,
            source=source,
            source_type=source_type,
            content=content,
            chunks=embedded_chunks,
            metadata=base_metadata,
            user_id=user_id,
            user_email=user_email,
            is_public=is_public,
        )

        logger.info(f"Saved document to MongoDB with ID: {document_id}")

        # Ingest into Graphiti if enabled
        if self.graphiti_adapter:
            try:
                graphiti_result = await self.graphiti_adapter.ingest_document(
                    document_id=document_id,
                    chunks=embedded_chunks,
                    metadata=base_metadata,
                    title=final_title,
                    source=source,
                )
                if graphiti_result.get("errors"):
                    errors.extend(graphiti_result["errors"])
                logger.info(
                    f"Graphiti ingestion: {graphiti_result.get('facts_added', 0)} facts "
                    f"from {graphiti_result.get('chunks_processed', 0)} chunks"
                )
            except Exception as e:
                error_msg = f"Graphiti ingestion failed: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        # Extract code examples if enabled
        if extract_code_examples and self.settings.use_agentic_rag:
            try:
                code_result = await ingest_code_examples(
                    self.mongo_client,
                    document_id,
                    content,
                    source,
                    base_metadata,
                )
                if code_result.get("errors"):
                    errors.extend(code_result["errors"])
                logger.info(
                    f"Code examples: {code_result.get('code_examples_stored', 0)} stored "
                    f"from {code_result.get('code_examples_extracted', 0)} extracted"
                )
            except Exception as e:
                error_msg = f"Code example extraction failed: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentIngestionResult(
            document_id=document_id,
            title=final_title,
            source=source,
            source_type=source_type,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
            errors=errors,
        )

    async def check_duplicate(self, source: str) -> str | None:
        """
        Check if content from this source already exists.

        Args:
            source: Source URL or identifier

        Returns:
            Document ID if duplicate exists, None otherwise
        """
        if not self._initialized:
            await self.initialize()

        documents_collection = self.db[self.settings.mongodb_collection_documents]
        existing = await documents_collection.find_one({"source": source}, {"_id": 1})

        if existing:
            return str(existing["_id"])
        return None

    async def check_youtube_duplicate(self, video_id: str) -> tuple[str | None, str | None]:
        """
        Check if a YouTube video already exists in the knowledge base.

        This method searches by video_id in metadata, which handles all URL variations:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/watch?v=VIDEO_ID&t=123  (timestamp)
        - https://www.youtube.com/watch?v=VIDEO_ID&list=PLxxx  (playlist)
        - https://www.youtube.com/watch?v=VIDEO_ID&si=xxx  (share tracking)

        Args:
            video_id: YouTube video ID (extracted from URL)

        Returns:
            Tuple of (document_id, source_url) if duplicate exists, (None, None) otherwise
        """
        if not self._initialized:
            await self.initialize()

        documents_collection = self.db[self.settings.mongodb_collection_documents]

        # Search by video_id in metadata (handles all URL variations)
        existing = await documents_collection.find_one(
            {
                "source_type": "youtube",
                "metadata.video_id": video_id,
            },
            {"_id": 1, "source": 1, "title": 1},
        )

        if existing:
            logger.info(
                f"Found existing YouTube document for video_id={video_id}: "
                f"doc_id={existing['_id']}, title={existing.get('title', 'Unknown')}"
            )
            return str(existing["_id"]), existing.get("source")

        return None, None

    async def delete_youtube_by_video_id(self, video_id: str) -> bool:
        """
        Delete a YouTube document and its chunks by video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()

        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Find document by video_id
        doc = await documents_collection.find_one(
            {
                "source_type": "youtube",
                "metadata.video_id": video_id,
            },
            {"_id": 1, "source": 1},
        )

        if not doc:
            return False

        document_id = doc["_id"]
        source = doc.get("source", video_id)

        # Delete chunks first
        chunks_result = await chunks_collection.delete_many({"document_id": document_id})

        # Delete document
        await documents_collection.delete_one({"_id": document_id})

        logger.info(
            f"Deleted YouTube document video_id={video_id}: "
            f"doc_id={document_id}, chunks_deleted={chunks_result.deleted_count}, source={source}"
        )
        return True

    async def delete_by_source(self, source: str) -> bool:
        """
        Delete document and its chunks by source.

        Args:
            source: Source URL or identifier

        Returns:
            True if deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()

        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Find document
        doc = await documents_collection.find_one({"source": source}, {"_id": 1})
        if not doc:
            return False

        document_id = doc["_id"]

        # Delete chunks first
        await chunks_collection.delete_many({"document_id": document_id})

        # Delete document
        await documents_collection.delete_one({"_id": document_id})

        logger.info(f"Deleted document and chunks for source: {source}")
        return True

    async def ingest_scraped_content(
        self,
        scraped: "ScrapedContent",
    ) -> ContentIngestionResult:
        """
        Ingest normalized ScrapedContent into the RAG pipeline.

        This is the unified entry point for all content ingestion. It accepts
        a ScrapedContent object and handles:
        - Chunk-by-chapters if chapters are provided and option is enabled
        - Graphiti episode creation with proper temporal anchoring
        - MongoDB storage with RLS fields
        - Code example extraction

        Args:
            scraped: Normalized ScrapedContent object from any source

        Returns:
            ContentIngestionResult with document ID and statistics

        Example:
            from app.core.models import ScrapedContent, IngestionOptions

            scraped = ScrapedContent(
                content="# My Document\\n...",
                title="My Document",
                source="https://example.com",
                source_type="web",
                metadata={"domain": "example.com"},
                user_email="user@example.com",
                options=IngestionOptions(chunk_by_chapters=True),
            )

            result = await service.ingest_scraped_content(scraped)
        """
        from capabilities.retrieval.graphiti_rag.ingestion.adapter import (
            ChapterInfo,
            GraphitiIngestionOptions,
        )

        from app.core.models import IngestionOptions

        # Get options with defaults
        options = scraped.options or IngestionOptions()

        # Convert chapter models if present
        graphiti_chapters = None
        if scraped.chapters and options.chunk_by_chapters:
            graphiti_chapters = [
                ChapterInfo(
                    title=ch.title,
                    start_time=ch.start_time,
                    end_time=ch.end_time,
                    content=ch.content,
                )
                for ch in scraped.chapters
            ]

        # Create Graphiti ingestion options
        graphiti_options = GraphitiIngestionOptions(
            create_episode=options.create_graphiti_episode and not options.skip_graphiti,
            episode_type=options.graphiti_episode_type,
            extract_facts=options.extract_facts and not options.skip_graphiti,
            reference_time=scraped.get_reference_time(),
            chapters=graphiti_chapters,
        )

        # If chunk_by_chapters is enabled and we have chapters with content,
        # we should chunk differently
        if options.chunk_by_chapters and scraped.has_chapters():
            return await self._ingest_with_chapters(scraped, options, graphiti_options)

        # Standard ingestion
        return await self._ingest_standard(scraped, options, graphiti_options)

    async def _ingest_standard(
        self,
        scraped: "ScrapedContent",
        options: "IngestionOptions",
        graphiti_options: "GraphitiIngestionOptions",
    ) -> ContentIngestionResult:
        """Standard ingestion without chapter-based chunking."""

        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        errors: list[str] = []

        # Build metadata including source-specific fields
        base_metadata = {
            "source_type": scraped.source_type,
            "ingested_at": datetime.now().isoformat(),
            **scraped.metadata,
        }

        # Extract frontmatter metadata if present
        frontmatter = self._extract_metadata_from_content(scraped.content)
        base_metadata.update(frontmatter)

        logger.info(f"Ingesting scraped content: {scraped.title} ({scraped.source_type})")

        # Convert to DoclingDocument if requested
        docling_doc = None
        if options.use_docling:
            docling_doc = self._convert_markdown_to_docling(scraped.content)
            if docling_doc:
                base_metadata["docling_converted"] = True

        # Chunk the document
        chunks = await self.chunker.chunk_document(
            content=scraped.content,
            title=scraped.title,
            source=scraped.source,
            metadata=base_metadata,
            docling_doc=docling_doc,
        )

        if not chunks:
            return ContentIngestionResult(
                document_id="",
                title=scraped.title,
                source=scraped.source,
                source_type=scraped.source_type,
                chunks_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created from content"],
            )

        logger.info(f"Created {len(chunks)} chunks")

        # Generate embeddings
        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        # Save to MongoDB (unless skipped)
        document_id = ""
        if not options.skip_mongodb:
            document_id = await self._save_to_mongodb(
                title=scraped.title,
                source=scraped.source,
                source_type=scraped.source_type,
                content=scraped.content,
                chunks=embedded_chunks,
                metadata=base_metadata,
                user_id=scraped.user_id,
                user_email=scraped.user_email,
                is_public=scraped.is_public,
            )
            logger.info(f"Saved document to MongoDB with ID: {document_id}")
        else:
            logger.info("MongoDB storage skipped per options")

        # Ingest into Graphiti if enabled
        episodes_created = 0
        facts_added = 0
        if self.graphiti_adapter and not options.skip_graphiti:
            try:
                graphiti_result = await self.graphiti_adapter.ingest_document(
                    document_id=document_id or "no-mongo-id",
                    chunks=embedded_chunks,
                    metadata=base_metadata,
                    title=scraped.title,
                    source=scraped.source,
                    options=graphiti_options,
                )
                episodes_created = graphiti_result.get("episodes_created", 0)
                facts_added = graphiti_result.get("facts_added", 0)
                if graphiti_result.get("errors"):
                    errors.extend(graphiti_result["errors"])
                logger.info(
                    f"Graphiti ingestion: {episodes_created} episodes, {facts_added} facts "
                    f"from {graphiti_result.get('chunks_processed', 0)} chunks"
                )
            except Exception as e:
                error_msg = f"Graphiti ingestion failed: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        # Extract code examples if enabled
        if (
            options.extract_code_examples
            and self.settings.use_agentic_rag
            and not options.skip_mongodb
            and document_id
        ):
            try:
                code_result = await ingest_code_examples(
                    self.mongo_client,
                    document_id,
                    scraped.content,
                    scraped.source,
                    base_metadata,
                )
                if code_result.get("errors"):
                    errors.extend(code_result["errors"])
                logger.info(
                    f"Code examples: {code_result.get('code_examples_stored', 0)} stored "
                    f"from {code_result.get('code_examples_extracted', 0)} extracted"
                )
            except Exception as e:
                error_msg = f"Code example extraction failed: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentIngestionResult(
            document_id=document_id,
            title=scraped.title,
            source=scraped.source,
            source_type=scraped.source_type,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
            errors=errors,
        )

    async def _ingest_with_chapters(
        self,
        scraped: "ScrapedContent",
        options: "IngestionOptions",
        graphiti_options: "GraphitiIngestionOptions",
    ) -> ContentIngestionResult:
        """Ingest content using chapters as chunk boundaries."""

        if not self._initialized:
            await self.initialize()

        start_time = datetime.now()
        errors: list[str] = []

        # Build metadata
        base_metadata = {
            "source_type": scraped.source_type,
            "ingested_at": datetime.now().isoformat(),
            "chapter_count": len(scraped.chapters) if scraped.chapters else 0,
            **scraped.metadata,
        }

        logger.info(f"Ingesting with chapters: {scraped.title} ({len(scraped.chapters)} chapters)")

        # Create chunks from chapters
        chunks = []
        for idx, chapter in enumerate(scraped.chapters or []):
            if not chapter.content:
                continue

            chunk_metadata = {
                **base_metadata,
                "chunk_type": "chapter",
                "chapter_title": chapter.title,
                "chapter_index": idx,
                "start_time": chapter.start_time,
                "end_time": chapter.end_time,
            }

            chunk = DocumentChunk(
                content=f"## {chapter.title}\n\n{chapter.content}",
                index=idx,
                start_char=0,
                end_char=len(chapter.content),
                metadata=chunk_metadata,
                token_count=len(chapter.content.split()),
            )
            chunks.append(chunk)

        if not chunks:
            # Fall back to standard ingestion
            logger.warning("No chapter content available, falling back to standard chunking")
            return await self._ingest_standard(scraped, options, graphiti_options)

        logger.info(f"Created {len(chunks)} chapter-based chunks")

        # Generate embeddings
        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        # Save to MongoDB
        document_id = ""
        if not options.skip_mongodb:
            document_id = await self._save_to_mongodb(
                title=scraped.title,
                source=scraped.source,
                source_type=scraped.source_type,
                content=scraped.content,
                chunks=embedded_chunks,
                metadata=base_metadata,
                user_id=scraped.user_id,
                user_email=scraped.user_email,
                is_public=scraped.is_public,
            )
            logger.info(f"Saved document to MongoDB with ID: {document_id}")

        # Ingest into Graphiti
        episodes_created = 0
        facts_added = 0
        if self.graphiti_adapter and not options.skip_graphiti:
            try:
                graphiti_result = await self.graphiti_adapter.ingest_document(
                    document_id=document_id or "no-mongo-id",
                    chunks=embedded_chunks,
                    metadata=base_metadata,
                    title=scraped.title,
                    source=scraped.source,
                    options=graphiti_options,
                )
                episodes_created = graphiti_result.get("episodes_created", 0)
                facts_added = graphiti_result.get("facts_added", 0)
                if graphiti_result.get("errors"):
                    errors.extend(graphiti_result["errors"])
            except Exception as e:
                error_msg = f"Graphiti ingestion failed: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentIngestionResult(
            document_id=document_id,
            title=scraped.title,
            source=scraped.source,
            source_type=scraped.source_type,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
            errors=errors,
        )


# Factory function for convenience
def create_content_ingestion_service(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_tokens: int = 512,
) -> ContentIngestionService:
    """
    Create a ContentIngestionService instance.

    Args:
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        max_tokens: Maximum tokens per chunk

    Returns:
        ContentIngestionService instance (call initialize() before use)
    """
    return ContentIngestionService(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_tokens=max_tokens,
    )
