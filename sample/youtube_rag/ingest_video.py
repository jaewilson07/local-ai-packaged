#!/usr/bin/env python3
"""
Sample script demonstrating YouTube RAG video ingestion.

This script shows how to use the YouTube RAG MCP tool to ingest a YouTube video
into the MongoDB RAG knowledge base.

Usage:
    python sample/youtube_rag/ingest_video.py [--url URL] [--extract-entities] [--extract-topics]

Examples:
    # Basic ingestion with chapters
    python sample/youtube_rag/ingest_video.py --url "https://www.youtube.com/watch?v=Lj9l-aXpCH8"

    # Full extraction with entities and topics
    python sample/youtube_rag/ingest_video.py --url "https://youtu.be/Lj9l-aXpCH8" --extract-entities --extract-topics
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "04-lambda"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(
    url: str,
    extract_entities: bool = False,
    extract_topics: bool = False,
    extract_key_moments: bool = False,
) -> None:
    """
    Ingest a YouTube video into the RAG knowledge base.

    Args:
        url: YouTube video URL
        extract_entities: Whether to extract entities using LLM
        extract_topics: Whether to classify topics using LLM
        extract_key_moments: Whether to extract key moments using LLM
    """
    from server.projects.youtube_rag.dependencies import YouTubeRAGDeps
    from server.projects.youtube_rag.models import IngestYouTubeRequest
    from server.projects.youtube_rag.tools import ingest_youtube_video

    logger.info(f"Starting YouTube ingestion for: {url}")

    deps = YouTubeRAGDeps.from_settings()
    await deps.initialize()

    try:
        request = IngestYouTubeRequest(
            url=url,
            extract_chapters=True,
            extract_entities=extract_entities,
            extract_topics=extract_topics,
            extract_key_moments=extract_key_moments,
            chunk_by_chapters=True,
        )

        result = await ingest_youtube_video(deps, request)

        print("\n" + "=" * 60)
        print("YouTube Ingestion Result")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Video ID: {result.video_id}")
        print(f"Title: {result.title}")
        print(f"Document ID: {result.document_id}")
        print(f"Chunks Created: {result.chunks_created}")
        print(f"Transcript Language: {result.transcript_language}")
        print(f"Chapters Found: {result.chapters_found}")

        if extract_entities:
            print(f"Entities Extracted: {result.entities_extracted}")

        if extract_topics:
            print(f"Topics: {', '.join(result.topics_classified)}")

        print(f"Processing Time: {result.processing_time_ms:.2f}ms")

        if result.errors:
            print(f"Errors: {result.errors}")

        print("=" * 60)

    finally:
        await deps.cleanup()


async def get_metadata_only(url: str) -> None:
    """
    Get video metadata without ingesting.

    Args:
        url: YouTube video URL
    """
    from server.projects.youtube_rag.dependencies import YouTubeRAGDeps
    from server.projects.youtube_rag.models import GetYouTubeMetadataRequest
    from server.projects.youtube_rag.tools import get_youtube_metadata

    logger.info(f"Getting metadata for: {url}")

    deps = YouTubeRAGDeps.from_settings()
    await deps.initialize()

    try:
        request = GetYouTubeMetadataRequest(
            url=url,
            include_transcript=False,
        )

        result = await get_youtube_metadata(deps, request)

        print("\n" + "=" * 60)
        print("YouTube Video Metadata")
        print("=" * 60)

        if result.metadata:
            meta = result.metadata
            print(f"Title: {meta.title}")
            print(f"Channel: {meta.channel_name}")
            print(f"Video ID: {meta.video_id}")
            print(f"Duration: {meta.duration_seconds // 60} minutes")
            print(f"Views: {meta.view_count:,}" if meta.view_count else "Views: N/A")
            print(f"Likes: {meta.like_count:,}" if meta.like_count else "Likes: N/A")
            print(f"Upload Date: {meta.upload_date}")
            print(f"Tags: {', '.join(meta.tags[:10])}" if meta.tags else "Tags: None")

        if result.chapters:
            print(f"\nChapters ({len(result.chapters)}):")
            for ch in result.chapters[:10]:
                minutes = int(ch.start_time // 60)
                seconds = int(ch.start_time % 60)
                print(f"  [{minutes:02d}:{seconds:02d}] {ch.title}")

        if result.errors:
            print(f"\nErrors: {result.errors}")

        print("=" * 60)

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest YouTube video into RAG")
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.youtube.com/watch?v=Lj9l-aXpCH8",
        help="YouTube video URL",
    )
    parser.add_argument(
        "--extract-entities",
        action="store_true",
        help="Extract entities using LLM (slower)",
    )
    parser.add_argument(
        "--extract-topics",
        action="store_true",
        help="Classify topics using LLM",
    )
    parser.add_argument(
        "--extract-key-moments",
        action="store_true",
        help="Extract key moments using LLM",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only get metadata, don't ingest",
    )

    args = parser.parse_args()

    if args.metadata_only:
        asyncio.run(get_metadata_only(args.url))
    else:
        asyncio.run(
            main(
                url=args.url,
                extract_entities=args.extract_entities,
                extract_topics=args.extract_topics,
                extract_key_moments=args.extract_key_moments,
            )
        )
