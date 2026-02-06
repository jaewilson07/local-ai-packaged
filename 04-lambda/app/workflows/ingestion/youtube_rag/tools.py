"""Core tool functions for YouTube RAG operations.

This module separates data extraction (via YouTubeClient) from ingestion
(via centralized ContentIngestionService in mongo_rag).

The unified ingestion uses:
- ScrapedContent model for normalized input
- ContentIngestionService.ingest_scraped_content() for processing
- Graphiti episodes for temporal anchoring
"""

import logging
from datetime import datetime
from typing import Any

from app.capabilities.retrieval.mongo_rag.ingestion.content_service import ContentIngestionService
from app.workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
from app.workflows.ingestion.youtube_rag.models import (
    GetYouTubeMetadataRequest,
    GetYouTubeMetadataResponse,
    IngestYouTubeRequest,
    IngestYouTubeResponse,
    YouTubeVideoData,
)
from app.workflows.ingestion.youtube_rag.services.extractors.entities import EntityExtractor
from app.workflows.ingestion.youtube_rag.services.extractors.topics import TopicExtractor
from app.workflows.ingestion.youtube_rag.services.youtube_client import (
    TranscriptNotAvailableError,
    VideoNotFoundError,
    YouTubeClient,
)

from shared.models import ChapterInfo, IngestionOptions, ScrapedContent

logger = logging.getLogger(__name__)


def _parse_upload_date(upload_date: str | None) -> datetime | None:
    """Parse YouTube upload date string to datetime."""
    if not upload_date:
        return None

    try:
        return datetime.strptime(upload_date, "%Y%m%d")
    except ValueError:
        try:
            return datetime.strptime(upload_date, "%Y-%m-%d")
        except ValueError:
            return None


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
            from workflows.ingestion.youtube_rag.services.youtube_client import YouTubeClient

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
    - Phase 0: Duplicate detection (by video ID, handles URL variations)
    - Phase 1: Extract video data via YouTubeClient (data acquisition)
    - Phase 2: Optional entity/topic extraction via LLM
    - Phase 3: Convert to ScrapedContent and ingest via unified pipeline

    The unified pipeline creates:
    - MongoDB documents with chunks and embeddings
    - Graphiti episodes for temporal queries (anchored to upload date)
    - Graphiti facts extracted from content

    Duplicate Detection:
    - Matches by video_id (not full URL) to catch variations like:
      - Timestamp links: ?v=xxx&t=123
      - Playlist links: ?v=xxx&list=PLyyy
      - Share tracking: ?v=xxx&si=zzz
      - Short URLs: youtu.be/xxx
    - Use skip_duplicates=False to allow re-ingestion
    - Use force_reindex=True to delete existing and re-ingest

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

        # Extract video ID (normalized from any URL format)
        video_id = YouTubeClient.extract_video_id(request.url)
        logger.info(f"Starting YouTube ingestion for video: {video_id}")

        # Phase 0: Initialize service and check for duplicates
        service = ContentIngestionService(
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        await service.initialize()

        try:
            existing_doc_id, existing_source = await service.check_youtube_duplicate(video_id)

            if existing_doc_id:
                if request.force_reindex:
                    # Delete existing and proceed with re-ingestion
                    logger.info(
                        f"force_reindex=True: Deleting existing document for video {video_id}"
                    )
                    await service.delete_youtube_by_video_id(video_id)
                elif request.skip_duplicates:
                    # Skip - video already exists
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000
                    logger.info(
                        f"Skipping duplicate video {video_id}: existing doc_id={existing_doc_id}"
                    )
                    await service.close()  # Clean up before returning
                    return IngestYouTubeResponse(
                        success=True,
                        url=request.url,
                        video_id=video_id,
                        document_id=existing_doc_id,
                        skipped=True,
                        skipped_reason=(
                            f"Video already exists in knowledge base. "
                            f"Original URL: {existing_source}. "
                            f"Use force_reindex=true to re-ingest."
                        ),
                        processing_time_ms=processing_time,
                    )
                # else: skip_duplicates=False, proceed with creating another document
        except Exception as e:
            # Don't fail ingestion if duplicate check fails
            logger.warning(f"Duplicate check failed for video {video_id}: {e}")
            errors.append(f"Duplicate check warning: {e}")

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
            logger.info("Extracting entities from transcript")
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
            logger.info("Classifying video topics")
            topic_extractor = TopicExtractor(openai_client=deps.openai_client)
            video_data.topics = await topic_extractor.classify_topics(
                transcript=video_data.transcript,
                metadata=video_data.metadata,
            )

        # Phase 3: Convert to ScrapedContent and ingest via unified pipeline
        logger.info("Ingesting video via unified ContentIngestionService")

        # Build metadata and markdown content
        metadata = _build_youtube_metadata(video_data)
        markdown_content = _create_youtube_markdown(video_data)

        # Convert chapters to ChapterInfo models
        chapters = None
        if video_data.chapters and video_data.transcript:
            from workflows.ingestion.youtube_rag.services.extractors.chapters import (
                ChapterExtractor,
            )

            # Get chapter content from transcript
            chapter_chunks = ChapterExtractor.chunk_transcript_by_chapters(
                video_data.transcript,
                video_data.chapters,
            )

            chapters = [
                ChapterInfo(
                    title=chunk["metadata"]["chapter_title"],
                    start_time=chunk["metadata"]["start_time"],
                    end_time=chunk["metadata"]["end_time"],
                    content=chunk["content"],
                )
                for chunk in chapter_chunks
            ]

        # Create ScrapedContent for unified ingestion
        scraped = ScrapedContent(
            content=markdown_content,
            title=video_data.metadata.title,
            source=request.url,
            source_type="youtube",
            metadata=metadata,
            reference_time=_parse_upload_date(video_data.metadata.upload_date),
            chapters=chapters,
            user_id=user_id,
            user_email=user_email,
            options=IngestionOptions(
                use_docling=True,
                extract_code_examples=False,  # YouTube videos rarely have code
                create_graphiti_episode=True,  # Create temporal episodes
                chunk_by_chapters=request.chunk_by_chapters and bool(chapters),
                graphiti_episode_type="both" if chapters else "overview",
                extract_facts=True,
            ),
        )

        # Ingest using the service (already initialized during duplicate check)
        try:
            ingestion_result = await service.ingest_scraped_content(scraped)

            errors.extend(ingestion_result.errors)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"YouTube ingestion complete: {ingestion_result.chunks_created} chunks created "
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
