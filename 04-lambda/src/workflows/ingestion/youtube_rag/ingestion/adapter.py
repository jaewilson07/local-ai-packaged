"""Adapter to bridge YouTube content with MongoDB RAG ingestion pipeline.

.. deprecated:: 2026-01
    This module is deprecated. Use the centralized ContentIngestionService instead:

    from server.projects.mongo_rag.ingestion.content_service import ContentIngestionService

    service = ContentIngestionService()
    await service.initialize()
    result = await service.ingest_content(
        content=markdown_content,
        title=video_title,
        source=video_url,
        source_type="youtube",
        metadata=video_metadata,
    )
    await service.close()

    Or use the /api/v1/rag/ingest/content endpoint directly.

    The YouTubeContentIngester class is kept for backward compatibility but will
    be removed in a future version.
"""

import logging
import warnings
from datetime import datetime
from typing import Any

from pymongo import AsyncMongoClient

from server.projects.graphiti_rag.config import config as graphiti_config
from server.projects.graphiti_rag.dependencies import GraphitiRAGDeps
from server.projects.graphiti_rag.ingestion.adapter import GraphitiIngestionAdapter
from server.projects.mongo_rag.ingestion.chunker import (
    ChunkingConfig,
    DocumentChunk,
    create_chunker,
)
from server.projects.mongo_rag.ingestion.embedder import create_embedder
from server.projects.mongo_rag.ingestion.pipeline import IngestionResult
from server.projects.youtube_rag.config import config
from server.projects.youtube_rag.models import (
    YouTubeVideoData,
)
from server.projects.youtube_rag.services.extractors.chapters import ChapterExtractor

logger = logging.getLogger(__name__)


class YouTubeContentIngester:
    """
    Ingests YouTube video content into MongoDB using existing RAG pipeline.

    .. deprecated:: 2026-01
        Use ContentIngestionService from server.projects.mongo_rag.ingestion.content_service
        instead. This class is kept for backward compatibility but will be removed.

    This adapter converts YouTube video data into the format expected by the
    MongoDB RAG ingestion pipeline, reusing chunking and embedding logic.
    """

    def __init__(
        self,
        mongo_client: AsyncMongoClient,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize ingester.

        Args:
            mongo_client: MongoDB client
            chunk_size: Chunk size for document splitting
            chunk_overlap: Chunk overlap size
        """
        warnings.warn(
            "YouTubeContentIngester is deprecated. Use ContentIngestionService from "
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
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Graphiti ingestion adapter (optional)
        self.graphiti_adapter: GraphitiIngestionAdapter | None = None
        self.graphiti_deps: GraphitiRAGDeps | None = None
        self._graphiti_initialized = False

    async def initialize(self) -> None:
        """
        Initialize Graphiti integration.

        Graphiti is enabled by default to automatically extract entities and
        relationships from video content. This can be disabled by setting
        USE_GRAPHITI=false in environment variables.
        """
        if self._graphiti_initialized:
            return

        # Initialize Graphiti if enabled
        if graphiti_config.use_graphiti:
            try:
                logger.info("Initializing Graphiti for youtube-rag")
                self.graphiti_deps = GraphitiRAGDeps.from_settings()
                await self.graphiti_deps.initialize()
                if self.graphiti_deps.graphiti:
                    self.graphiti_adapter = GraphitiIngestionAdapter(self.graphiti_deps.graphiti)
                    logger.info("Graphiti ingestion adapter initialized for youtube-rag")
                else:
                    logger.warning("Graphiti enabled but client not available")
            except Exception as e:
                logger.warning(f"Failed to initialize Graphiti: {e}")
                logger.info("Continuing without Graphiti ingestion")
        else:
            logger.info("Graphiti disabled via USE_GRAPHITI=false")

        self._graphiti_initialized = True

    def _build_metadata(
        self,
        video_data: YouTubeVideoData,
    ) -> dict[str, Any]:
        """
        Build metadata dictionary from video data.

        Args:
            video_data: Complete YouTube video data

        Returns:
            Metadata dictionary for storage
        """
        metadata = video_data.metadata

        result = {
            "source_type": "youtube",
            "video_id": metadata.video_id,
            "url": video_data.url,
            "channel_name": metadata.channel_name,
            "channel_id": metadata.channel_id,
            "upload_date": metadata.upload_date,
            "duration_seconds": metadata.duration_seconds,
            "view_count": metadata.view_count,
            "like_count": metadata.like_count,
            "comment_count": metadata.comment_count,
            "tags": metadata.tags,
            "categories": metadata.categories,
            "thumbnail_url": metadata.thumbnail_url,
            "is_live": metadata.is_live,
            "is_age_restricted": metadata.is_age_restricted,
            "ingested_at": datetime.now().isoformat(),
        }

        # Add transcript info
        if video_data.transcript:
            result["transcript_language"] = video_data.transcript.language
            result["transcript_is_generated"] = video_data.transcript.is_generated
            result["transcript_segment_count"] = len(video_data.transcript.segments)

        # Add chapters
        if video_data.chapters:
            result["chapters"] = [
                {
                    "title": ch.title,
                    "start_time": ch.start_time,
                    "end_time": ch.end_time,
                }
                for ch in video_data.chapters
            ]
            result["chapter_count"] = len(video_data.chapters)

        # Add extracted entities
        if video_data.entities:
            result["entities"] = [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "mentions": e.mentions,
                }
                for e in video_data.entities
            ]
            result["entity_count"] = len(video_data.entities)

        # Add relationships
        if video_data.relationships:
            result["relationships"] = [
                {
                    "source": r.source,
                    "target": r.target,
                    "relationship": r.relationship,
                }
                for r in video_data.relationships
            ]

        # Add topics
        if video_data.topics:
            result["topics"] = video_data.topics

        # Add key moments
        if video_data.key_moments:
            result["key_moments"] = video_data.key_moments

        return result

    def _create_content_markdown(
        self,
        video_data: YouTubeVideoData,
        include_chapters: bool = True,
    ) -> str:
        """
        Create markdown content from video data.

        Args:
            video_data: Complete YouTube video data
            include_chapters: Whether to include chapter markers

        Returns:
            Markdown formatted content
        """
        parts = []

        # Title and metadata header
        parts.append(f"# {video_data.metadata.title}")
        parts.append("")
        parts.append(f"**Channel:** {video_data.metadata.channel_name}")
        if video_data.metadata.upload_date:
            parts.append(f"**Upload Date:** {video_data.metadata.upload_date}")
        if video_data.metadata.duration_seconds:
            duration_min = video_data.metadata.duration_seconds // 60
            parts.append(f"**Duration:** {duration_min} minutes")
        parts.append(f"**URL:** {video_data.url}")
        parts.append("")

        # Description excerpt
        if video_data.metadata.description:
            desc = video_data.metadata.description[:500]
            if len(video_data.metadata.description) > 500:
                desc += "..."
            parts.append("## Description")
            parts.append(desc)
            parts.append("")

        # Topics
        if video_data.topics:
            parts.append(f"**Topics:** {', '.join(video_data.topics)}")
            parts.append("")

        # Transcript
        if video_data.transcript:
            parts.append("## Transcript")
            parts.append("")

            if include_chapters and video_data.chapters:
                # Format with chapter markers
                from server.projects.youtube_rag.services.youtube_client import YouTubeClient

                client = YouTubeClient()
                formatted = client.format_transcript_with_timestamps(
                    video_data.transcript,
                    video_data.chapters,
                )
                parts.append(formatted)
            else:
                # Just the plain transcript
                parts.append(video_data.transcript.full_text)

        return "\n".join(parts)

    async def ingest_video(
        self,
        video_data: YouTubeVideoData,
        chunk_by_chapters: bool = True,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> IngestionResult:
        """
        Ingest a YouTube video into MongoDB.

        Args:
            video_data: Complete YouTube video data
            chunk_by_chapters: Whether to chunk by chapters if available
            chunk_size: Override chunk size (optional)
            chunk_overlap: Override chunk overlap (optional)

        Returns:
            IngestionResult with document ID and stats
        """
        start_time = datetime.now()

        try:
            title = video_data.metadata.title
            source = video_data.url
            metadata = self._build_metadata(video_data)

            # Create markdown content
            content = self._create_content_markdown(video_data)

            # Determine chunking strategy
            chunks: list[DocumentChunk] = []

            if chunk_by_chapters and video_data.chapters and video_data.transcript:
                # Chunk by chapters
                logger.info(f"Chunking by {len(video_data.chapters)} chapters")
                chapter_chunks = ChapterExtractor.chunk_transcript_by_chapters(
                    video_data.transcript,
                    video_data.chapters,
                )

                for idx, chapter_chunk in enumerate(chapter_chunks):
                    chunk_metadata = {
                        **metadata,
                        "chunk_type": "chapter",
                        "chapter_title": chapter_chunk["metadata"]["chapter_title"],
                        "start_time": chapter_chunk["metadata"]["start_time"],
                        "end_time": chapter_chunk["metadata"]["end_time"],
                    }

                    chunks.append(
                        DocumentChunk(
                            content=chapter_chunk["content"],
                            index=idx,
                            start_char=0,  # Not applicable for chapter-based
                            end_char=len(chapter_chunk["content"]),
                            metadata=chunk_metadata,
                            token_count=len(chapter_chunk["content"].split()),
                        )
                    )
            else:
                # Use standard chunking
                logger.info("Using standard text chunking")
                use_chunk_size = chunk_size or self.chunk_size
                use_chunk_overlap = chunk_overlap or self.chunk_overlap

                chunker_config = ChunkingConfig(
                    chunk_size=use_chunk_size,
                    chunk_overlap=use_chunk_overlap,
                    max_chunk_size=use_chunk_size * 2,
                    max_tokens=512,
                )
                chunker = create_chunker(chunker_config)

                chunks = await chunker.chunk_document(
                    content=content,
                    title=title,
                    source=source,
                    metadata=metadata,
                    docling_doc=None,
                )

            if not chunks:
                logger.warning(f"No chunks created for video {video_data.metadata.video_id}")
                return IngestionResult(
                    document_id="",
                    title=title,
                    chunks_created=0,
                    processing_time_ms=0,
                    errors=["No chunks created"],
                )

            logger.info(f"Created {len(chunks)} chunks for {title}")

            # Generate embeddings
            embedded_chunks = await self.embedder.embed_chunks(chunks)
            logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

            # Save to MongoDB
            document_id = await self._save_to_mongodb(
                title=title,
                source=source,
                content=content,
                chunks=embedded_chunks,
                metadata=metadata,
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
                        source=source,
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
            logger.exception(f"Error ingesting video {video_data.url}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return IngestionResult(
                document_id="",
                title=video_data.metadata.title,
                chunks_created=0,
                processing_time_ms=processing_time,
                errors=[str(e)],
            )

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
                "embedding": chunk.embedding,
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
