"""Adapter to bridge MongoDB documents with Graphiti ingestion.

This adapter provides a unified interface for ingesting content into Graphiti,
supporting both episode creation (for temporal context) and fact extraction.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphiti_core import Graphiti

    GraphitiType = Graphiti
else:
    try:
        from graphiti_core import Graphiti

        GraphitiType = Graphiti
    except ImportError:
        GraphitiType = Any  # type: ignore

from capabilities.retrieval.graphiti_rag.ingestion.graph_builder import (
    create_document_episode,
    ingest_to_graphiti,
)
from capabilities.retrieval.mongo_rag.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class ChapterInfo:
    """Information about a content chapter/section."""

    title: str
    start_time: float  # seconds or character position
    end_time: float | None = None
    content: str | None = None


@dataclass
class GraphitiIngestionOptions:
    """Options for Graphiti ingestion behavior."""

    create_episode: bool = True
    episode_type: str = "overview"  # "overview", "chapters", "both"
    extract_facts: bool = True
    reference_time: datetime | None = None
    chapters: list[ChapterInfo] | None = None


class GraphitiIngestionAdapter:
    """
    Adapter to ingest MongoDB documents into Graphiti knowledge graph.

    This adapter takes documents that have been processed and stored in MongoDB
    and ingests them into Graphiti for knowledge graph construction.

    It supports:
    - Episode creation for temporal anchoring (recommended for all content)
    - Fact extraction from text chunks
    - Chapter-based episodes for structured content (videos, documents with sections)
    """

    def __init__(self, graphiti: GraphitiType | None = None):
        """
        Initialize adapter.

        Args:
            graphiti: Optional Graphiti client (will be initialized if not provided)
        """
        self.graphiti = graphiti

    async def ingest_document(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        metadata: dict[str, Any],
        title: str | None = None,
        source: str | None = None,
        options: GraphitiIngestionOptions | None = None,
    ) -> dict[str, Any]:
        """
        Ingest a document into Graphiti with episodes and facts.

        Args:
            document_id: MongoDB document ID
            chunks: List of document chunks
            metadata: Document metadata
            title: Document title
            source: Document source path
            options: Ingestion options (defaults to creating episode + extracting facts)

        Returns:
            Ingestion statistics including episodes_created and facts_added
        """
        if not self.graphiti:
            logger.warning("Graphiti client not available - skipping ingestion")
            return {
                "episodes_created": 0,
                "facts_added": 0,
                "chunks_processed": 0,
                "errors": [],
            }

        # Use default options if not provided
        if options is None:
            options = GraphitiIngestionOptions()

        result = {
            "episodes_created": 0,
            "facts_added": 0,
            "chunks_processed": 0,
            "total_chunks": len(chunks),
            "errors": [],
        }

        # Step 1: Create document episode(s) for temporal anchoring
        if options.create_episode:
            episode_result = await self._create_episodes(
                document_id=document_id,
                title=title or metadata.get("title", "Untitled"),
                source=source or metadata.get("source", "unknown"),
                metadata=metadata,
                options=options,
                chunks=chunks,
            )
            result["episodes_created"] = episode_result.get("episodes_created", 0)
            result["errors"].extend(episode_result.get("errors", []))

        # Step 2: Extract facts from chunks
        if options.extract_facts:
            facts_result = await ingest_to_graphiti(
                self.graphiti,
                document_id,
                chunks,
                metadata,
                title,
                source,
            )
            result["facts_added"] = facts_result.get("facts_added", 0)
            result["chunks_processed"] = facts_result.get("chunks_processed", 0)
            result["errors"].extend(facts_result.get("errors", []))

        logger.info(
            f"Graphiti ingestion complete for document {document_id}: "
            f"{result['episodes_created']} episodes, {result['facts_added']} facts"
        )

        return result

    async def _create_episodes(
        self,
        document_id: str,
        title: str,
        source: str,
        metadata: dict[str, Any],
        options: GraphitiIngestionOptions,
        chunks: list[DocumentChunk],
    ) -> dict[str, Any]:
        """
        Create Graphiti episodes for temporal anchoring.

        Args:
            document_id: MongoDB document ID
            title: Document title
            source: Document source
            metadata: Document metadata
            options: Ingestion options
            chunks: Document chunks (for content extraction)

        Returns:
            Dictionary with episodes_created count and errors
        """
        episodes_created = 0
        errors: list[str] = []

        # Determine reference time
        reference_time = options.reference_time
        if reference_time is None:
            # Try to extract from metadata
            ingested_at = metadata.get("ingested_at")
            if ingested_at:
                if isinstance(ingested_at, str):
                    try:
                        reference_time = datetime.fromisoformat(ingested_at)
                    except ValueError:
                        reference_time = datetime.now()
                elif isinstance(ingested_at, datetime):
                    reference_time = ingested_at
            else:
                reference_time = datetime.now()

        # Create overview episode
        if options.episode_type in ("overview", "both"):
            try:
                await create_document_episode(
                    graphiti=self.graphiti,
                    document_id=document_id,
                    title=title,
                    source=source,
                    source_type=metadata.get("source_type", "document"),
                    metadata=metadata,
                    reference_time=reference_time,
                    chunks=chunks,
                )
                episodes_created += 1
                logger.info(f"Created overview episode for document {document_id}")
            except Exception as e:
                error_msg = f"Error creating overview episode: {e!s}"
                logger.exception(error_msg)
                errors.append(error_msg)

        # Create chapter episodes if available
        if options.episode_type in ("chapters", "both") and options.chapters:
            for chapter in options.chapters:
                try:
                    await self._create_chapter_episode(
                        document_id=document_id,
                        chapter=chapter,
                        source=source,
                        base_reference_time=reference_time,
                    )
                    episodes_created += 1
                except Exception as e:
                    error_msg = f"Error creating chapter episode '{chapter.title}': {e!s}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        return {"episodes_created": episodes_created, "errors": errors}

    async def _create_chapter_episode(
        self,
        document_id: str,
        chapter: ChapterInfo,
        source: str,
        base_reference_time: datetime,
    ) -> None:
        """Create an episode for a specific chapter."""
        try:
            from datetime import timedelta

            from graphiti_core import EpisodeType
        except ImportError:
            logger.warning("graphiti_core not installed, skipping chapter episode")
            return

        if not chapter.content:
            logger.warning(f"Chapter '{chapter.title}' has no content, skipping")
            return

        # Anchor to base time + chapter offset
        chapter_time = base_reference_time + timedelta(seconds=chapter.start_time)

        await self.graphiti.add_episode(
            name=f"doc:{document_id}:chapter:{chapter.title[:50]}",
            episode_body=chapter.content,
            source=EpisodeType.text,
            source_description=f"Chapter: {chapter.title}",
            reference_time=chapter_time,
        )
