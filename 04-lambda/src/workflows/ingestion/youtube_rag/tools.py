"""Core tool functions for YouTube RAG operations.

This module separates data extraction (via YouTubeClient) from ingestion
(via centralized ContentIngestionService in mongo_rag).
"""

import logging
from datetime import datetime
from typing import Any

from server.projects.mongo_rag.ingestion.content_service import ContentIngestionService
from server.projects.youtube_rag.dependencies import YouTubeRAGDeps
from server.projects.youtube_rag.models import (
    GetYouTubeMetadataRequest,
    GetYouTubeMetadataResponse,
    IngestYouTubeRequest,
    IngestYouTubeResponse,
    YouTubeVideoData,
)
from server.projects.youtube_rag.services.extractors.entities import EntityExtractor
from server.projects.youtube_rag.services.extractors.topics import TopicExtractor
from server.projects.youtube_rag.services.youtube_client import (
    TranscriptNotAvailableError,
    VideoNotFoundError,
    YouTubeClient,
)

logger = logging.getLogger(__name__)


def _build_youtube_metadata(video_data: YouTubeVideoData) -> dict[str, Any]:
    """
    Build metadata dictionary from YouTube video data.

    Args:
        video_data: Complete YouTube video data

    Returns:
        Metadata dictionary for storage
    """
    metadata = video_data.metadata

    result = {
        "video_id": metadata.video_id,
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


def _create_youtube_markdown(video_data: YouTubeVideoData) -> str:
    """
    Create markdown content from YouTube video data.

    Args:
        video_data: Complete YouTube video data

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

        if video_data.chapters:
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


async def ingest_youtube_video(
    deps: YouTubeRAGDeps,
    request: IngestYouTubeRequest,
    user_id: str | None = None,
    user_email: str | None = None,
) -> IngestYouTubeResponse:
    """
    Ingest a YouTube video into the MongoDB RAG knowledge base.

    This function performs:
    - Phase 1: Extract video data via YouTubeClient (data acquisition)
    - Phase 2: Optional entity/topic extraction via LLM
    - Phase 3: Ingest via ContentIngestionService (centralized storage)

    Args:
        deps: YouTube RAG dependencies
        request: Ingestion request with URL and options
        user_id: Optional user ID for RLS
        user_email: Optional user email for RLS

    Returns:
        IngestYouTubeResponse with results
    """
    start_time = datetime.now()
    errors: list[str] = []

    try:
        # Ensure dependencies are initialized
        if not deps.youtube_client:
            await deps.initialize()

        # Extract video ID
        video_id = YouTubeClient.extract_video_id(request.url)
        logger.info(f"🎬 Starting YouTube ingestion for video: {video_id}")

        # Phase 1: Get video data (data acquisition)
        video_data = await deps.youtube_client.get_video_data(
            url=request.url,
            include_transcript=True,
            include_chapters=request.extract_chapters,
            preferred_language=request.preferred_language,
        )

        # Check if transcript is available
        if not video_data.transcript:
            errors.append("Transcript not available for this video")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            return IngestYouTubeResponse(
                success=False,
                url=request.url,
                video_id=video_id,
                title=video_data.metadata.title,
                errors=errors,
                processing_time_ms=processing_time,
            )

        # Phase 2: Extract entities if requested
        if request.extract_entities and deps.openai_client:
            logger.info("🔍 Extracting entities from transcript")
            entity_extractor = EntityExtractor(openai_client=deps.openai_client)
            video_data.entities = await entity_extractor.extract_entities(
                transcript=video_data.transcript,
                video_title=video_data.metadata.title,
                video_description=video_data.metadata.description,
            )

            # Also extract relationships if we have entities
            if video_data.entities:
                video_data.relationships = await entity_extractor.extract_relationships(
                    transcript=video_data.transcript,
                    entities=video_data.entities,
                )

            # Extract key moments if requested
            if request.extract_key_moments:
                video_data.key_moments = await entity_extractor.extract_key_moments(
                    transcript=video_data.transcript,
                    video_title=video_data.metadata.title,
                )

        # Classify topics if requested
        if request.extract_topics and deps.openai_client:
            logger.info("📚 Classifying video topics")
            topic_extractor = TopicExtractor(openai_client=deps.openai_client)
            video_data.topics = await topic_extractor.classify_topics(
                transcript=video_data.transcript,
                metadata=video_data.metadata,
            )

        # Phase 3: Ingest using centralized ContentIngestionService
        logger.info("💾 Ingesting video via ContentIngestionService")

        # Build metadata and markdown content
        metadata = _build_youtube_metadata(video_data)
        markdown_content = _create_youtube_markdown(video_data)

        service = ContentIngestionService(
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        try:
            await service.initialize()

            ingestion_result = await service.ingest_content(
                content=markdown_content,
                title=video_data.metadata.title,
                source=request.url,
                source_type="youtube",
                metadata=metadata,
                user_id=user_id,
                user_email=user_email,
                use_docling=True,  # Use Docling for structure-aware chunking
            )

            errors.extend(ingestion_result.errors)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"✅ YouTube ingestion complete: {ingestion_result.chunks_created} chunks created "
                f"in {processing_time:.2f}ms"
            )

            return IngestYouTubeResponse(
                success=len(errors) == 0,
                url=request.url,
                video_id=video_id,
                title=video_data.metadata.title,
                document_id=ingestion_result.document_id,
                chunks_created=ingestion_result.chunks_created,
                transcript_language=(
                    video_data.transcript.language if video_data.transcript else None
                ),
                chapters_found=len(video_data.chapters),
                entities_extracted=len(video_data.entities),
                topics_classified=video_data.topics,
                processing_time_ms=processing_time,
                errors=errors,
            )

        finally:
            await service.close()

    except VideoNotFoundError as e:
        logger.warning(f"Video not found: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        return IngestYouTubeResponse(
            success=False,
            url=request.url,
            video_id=YouTubeClient.extract_video_id(request.url),
            errors=[str(e)],
            processing_time_ms=processing_time,
        )

    except TranscriptNotAvailableError as e:
        logger.warning(f"Transcript not available: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        video_id = YouTubeClient.extract_video_id(request.url)
        return IngestYouTubeResponse(
            success=False,
            url=request.url,
            video_id=video_id,
            errors=[str(e)],
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.exception(f"Error ingesting YouTube video: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        try:
            video_id = YouTubeClient.extract_video_id(request.url)
        except ValueError:
            video_id = ""
        return IngestYouTubeResponse(
            success=False,
            url=request.url,
            video_id=video_id,
            errors=[str(e)],
            processing_time_ms=processing_time,
        )


async def get_youtube_metadata(
    deps: YouTubeRAGDeps,
    request: GetYouTubeMetadataRequest,
) -> GetYouTubeMetadataResponse:
    """
    Get YouTube video metadata without ingesting.

    Args:
        deps: YouTube RAG dependencies
        request: Metadata request

    Returns:
        GetYouTubeMetadataResponse with video metadata
    """
    errors: list[str] = []

    try:
        # Ensure dependencies are initialized
        if not deps.youtube_client:
            await deps.initialize()

        # Get video data
        video_data = await deps.youtube_client.get_video_data(
            url=request.url,
            include_transcript=request.include_transcript,
            include_chapters=True,
        )

        return GetYouTubeMetadataResponse(
            success=True,
            url=request.url,
            metadata=video_data.metadata,
            transcript=video_data.transcript if request.include_transcript else None,
            chapters=video_data.chapters,
            errors=errors,
        )

    except VideoNotFoundError as e:
        logger.warning(f"Video not found: {e}")
        return GetYouTubeMetadataResponse(
            success=False,
            url=request.url,
            errors=[str(e)],
        )

    except Exception as e:
        logger.exception(f"Error getting YouTube metadata: {e}")
        return GetYouTubeMetadataResponse(
            success=False,
            url=request.url,
            errors=[str(e)],
        )
