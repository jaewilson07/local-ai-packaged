"""YouTube-specific Graphiti ingestion with temporal episode support.

This module provides smart temporal ingestion for YouTube videos into Graphiti,
creating episodes anchored to video timestamps for accurate temporal queries.
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from graphiti_core import Graphiti

from workflows.ingestion.youtube_rag.models import (
    VideoChapter,
    VideoTranscript,
    YouTubeVideoData,
)

logger = logging.getLogger(__name__)


def _parse_upload_date(upload_date: str | None) -> datetime:
    """
    Parse YouTube upload date string to datetime.

    Args:
        upload_date: Upload date in YYYYMMDD format

    Returns:
        datetime object (defaults to now if parsing fails)
    """
    if not upload_date:
        return datetime.now()

    try:
        return datetime.strptime(upload_date, "%Y%m%d")
    except ValueError:
        try:
            return datetime.strptime(upload_date, "%Y-%m-%d")
        except ValueError:
            return datetime.now()


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _get_chapter_transcript(
    transcript: VideoTranscript,
    chapter: VideoChapter,
) -> str:
    """
    Extract transcript text for a specific chapter.

    Args:
        transcript: Full video transcript
        chapter: Chapter with start/end times

    Returns:
        Transcript text for the chapter
    """
    chapter_texts = []
    end_time = chapter.end_time or float("inf")

    for segment in transcript.segments:
        if segment.start >= chapter.start_time and segment.start < end_time:
            chapter_texts.append(segment.text)

    return " ".join(chapter_texts)


def _create_overview_text(video_data: YouTubeVideoData) -> str:
    """
    Create an overview episode text from video metadata.

    Args:
        video_data: Complete YouTube video data

    Returns:
        Formatted overview text
    """
    parts = [
        f"Video Title: {video_data.metadata.title}",
        f"Channel: {video_data.metadata.channel_name}",
    ]

    if video_data.metadata.description:
        desc = video_data.metadata.description[:500]
        if len(video_data.metadata.description) > 500:
            desc += "..."
        parts.append(f"Description: {desc}")

    if video_data.topics:
        parts.append(f"Topics: {', '.join(video_data.topics)}")

    if video_data.metadata.tags:
        parts.append(f"Tags: {', '.join(video_data.metadata.tags[:10])}")

    if video_data.chapters:
        chapter_list = ", ".join(ch.title for ch in video_data.chapters[:10])
        parts.append(f"Chapters: {chapter_list}")

    if video_data.entities:
        entity_list = ", ".join(e.name for e in video_data.entities[:10])
        parts.append(f"Key Entities: {entity_list}")

    return "\n".join(parts)


async def ingest_youtube_to_graphiti(
    graphiti: "Graphiti",
    video_data: YouTubeVideoData,
    document_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Ingest YouTube video into Graphiti with smart temporal handling.

    Creates episodes for:
    - Video overview (anchored to upload_date)
    - Each chapter (anchored to chapter timestamp within video)
    - Key moments (anchored to moment timestamp)

    Args:
        graphiti: Initialized Graphiti client
        video_data: Complete YouTube video data
        document_id: MongoDB document ID for reference
        user_id: Optional user ID for scoping

    Returns:
        Dictionary with ingestion statistics
    """
    if not graphiti:
        logger.warning("Graphiti client not available - skipping ingestion")
        return {"episodes_created": 0, "errors": ["Graphiti not available"]}

    episodes_created = 0
    errors: list[str] = []

    # Parse upload_date to datetime
    reference_time = _parse_upload_date(video_data.metadata.upload_date)
    video_id = video_data.metadata.video_id

    try:
        # Import EpisodeType here to avoid import errors when graphiti isn't installed
        try:
            from graphiti_core import EpisodeType
        except ImportError:
            logger.warning("graphiti_core not installed, using string episode type")
            EpisodeType = None

        episode_type = EpisodeType.text if EpisodeType else "text"

        # 1. Video overview episode
        logger.info(f"Creating overview episode for video {video_id}")
        overview_text = _create_overview_text(video_data)

        await graphiti.add_episode(
            name=f"youtube:{video_id}:overview",
            episode_body=overview_text,
            source=episode_type,
            source_description=f"YouTube: {video_data.metadata.channel_name}",
            reference_time=reference_time,
        )
        episodes_created += 1

        # 2. Chapter episodes (each with its own temporal anchor)
        if video_data.chapters and video_data.transcript:
            logger.info(f"Creating {len(video_data.chapters)} chapter episodes")

            for chapter in video_data.chapters:
                try:
                    # Anchor to video upload time + chapter offset
                    chapter_time = reference_time + timedelta(seconds=chapter.start_time)
                    chapter_transcript = _get_chapter_transcript(video_data.transcript, chapter)

                    if not chapter_transcript.strip():
                        continue

                    await graphiti.add_episode(
                        name=f"youtube:{video_id}:chapter:{chapter.title[:50]}",
                        episode_body=chapter_transcript,
                        source=episode_type,
                        source_description=(
                            f"Chapter: {chapter.title} @ {_format_timestamp(chapter.start_time)}"
                        ),
                        reference_time=chapter_time,
                    )
                    episodes_created += 1

                except Exception as e:
                    error_msg = f"Error creating chapter episode '{chapter.title}': {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        # 3. Key moments episodes
        if video_data.key_moments:
            logger.info(f"Creating {len(video_data.key_moments)} key moment episodes")

            for moment in video_data.key_moments:
                try:
                    moment_time = reference_time + timedelta(seconds=moment.get("timestamp", 0))
                    moment_text = (
                        f"Key Moment: {moment.get('title', 'Untitled')}\n"
                        f"{moment.get('description', '')}"
                    )

                    await graphiti.add_episode(
                        name=f"youtube:{video_id}:moment:{moment.get('title', 'unknown')[:30]}",
                        episode_body=moment_text,
                        source=episode_type,
                        source_description=(
                            f"Key Moment @ {_format_timestamp(moment.get('timestamp', 0))}"
                        ),
                        reference_time=moment_time,
                    )
                    episodes_created += 1

                except Exception as e:
                    error_msg = f"Error creating moment episode: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        # 4. Full transcript episode (if no chapters)
        if not video_data.chapters and video_data.transcript:
            logger.info("Creating full transcript episode (no chapters found)")

            await graphiti.add_episode(
                name=f"youtube:{video_id}:transcript",
                episode_body=video_data.transcript.full_text,
                source=episode_type,
                source_description=f"Full Transcript: {video_data.metadata.title}",
                reference_time=reference_time,
            )
            episodes_created += 1

        logger.info(
            f"Graphiti ingestion complete for video {video_id}: "
            f"{episodes_created} episodes created"
        )

    except Exception as e:
        error_msg = f"Graphiti ingestion error: {e}"
        logger.exception(error_msg)
        errors.append(error_msg)

    return {
        "episodes_created": episodes_created,
        "video_id": video_id,
        "document_id": document_id,
        "errors": errors,
    }
