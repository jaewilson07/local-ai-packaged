#!/usr/bin/env python3
"""
Sample script demonstrating YouTube RAG video ingestion with Graphiti temporal episodes.

This script shows how to:
1. Extract transcript from a YouTube video
2. Ingest video into MongoDB RAG with embeddings
3. Create temporal episodes in Graphiti for smart temporal queries

Usage:
    python sample/youtube_rag/ingest_video.py [--url URL] [--extract-entities] [--extract-topics]

Examples:
    # Basic ingestion with chapters
    python sample/youtube_rag/ingest_video.py --url "https://www.youtube.com/watch?v=A3DKwLORVe4"

    # Full extraction with entities and topics
    python sample/youtube_rag/ingest_video.py --url "https://youtu.be/A3DKwLORVe4" --extract-entities --extract-topics
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
lambda_src_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default video URL for testing
DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=A3DKwLORVe4"


async def ingest_youtube_video(
    url: str,
    extract_entities: bool = False,
    extract_topics: bool = False,
    extract_key_moments: bool = False,
    save_transcript: bool = True,
) -> dict:
    """
    Ingest a YouTube video into the RAG knowledge base.

    Args:
        url: YouTube video URL
        extract_entities: Whether to extract entities using LLM
        extract_topics: Whether to classify topics using LLM
        extract_key_moments: Whether to extract key moments using LLM
        save_transcript: Whether to save transcript to file

    Returns:
        Ingestion result dictionary
    """
    from workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
    from workflows.ingestion.youtube_rag.models import IngestYouTubeRequest
    from workflows.ingestion.youtube_rag.tools import (
        ingest_youtube_video as do_ingest,
    )

    logger.info(f"Starting YouTube ingestion for: {url}")

    deps = YouTubeRAGDeps.from_settings(skip_mongodb=True)
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

        result = await do_ingest(deps, request)

        # Print results
        print("\n" + "=" * 70)
        print("🎬 YouTube Ingestion Result")
        print("=" * 70)
        print(f"✅ Success: {result.success}")
        print(f"📹 Video ID: {result.video_id}")
        print(f"📝 Title: {result.title}")
        print(f"🆔 Document ID: {result.document_id}")
        print(f"📦 Chunks Created: {result.chunks_created}")
        print(f"🌐 Transcript Language: {result.transcript_language}")
        print(f"📑 Chapters Found: {result.chapters_found}")

        if extract_entities:
            print(f"👤 Entities Extracted: {result.entities_extracted}")

        if extract_topics and result.topics_classified:
            print(f"🏷️  Topics: {', '.join(result.topics_classified)}")

        print(f"🔗 Graphiti Episodes: {result.graphiti_episodes_created}")
        print(f"⏱️  Processing Time: {result.processing_time_ms:.2f}ms")

        if result.errors:
            print(f"⚠️  Errors: {result.errors}")

        print("=" * 70)

        return result.model_dump()

    finally:
        await deps.cleanup()


async def get_transcript_only(url: str, output_file: str | None = None) -> str:
    """
    Extract transcript from YouTube video without ingesting.

    Args:
        url: YouTube video URL
        output_file: Optional file path to save transcript

    Returns:
        Transcript text
    """
    from workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps

    logger.info(f"Extracting transcript for: {url}")

    deps = YouTubeRAGDeps.from_settings(skip_mongodb=True)
    await deps.initialize()

    try:
        video_data = await deps.youtube_client.get_video_data(
            url=url,
            include_transcript=True,
            include_chapters=True,
        )

        print("\n" + "=" * 70)
        print("📜 YouTube Transcript Extraction")
        print("=" * 70)
        print(f"📹 Video ID: {video_data.metadata.video_id}")
        print(f"📝 Title: {video_data.metadata.title}")
        print(f"📺 Channel: {video_data.metadata.channel_name}")
        print(f"⏱️  Duration: {video_data.metadata.duration_seconds // 60} minutes")

        if video_data.transcript:
            print(f"🌐 Language: {video_data.transcript.language}")
            print(f"🤖 Auto-generated: {video_data.transcript.is_generated}")
            print(f"📊 Segments: {len(video_data.transcript.segments)}")
            print("=" * 70)

            # Format transcript with timestamps
            if video_data.chapters:
                formatted = deps.youtube_client.format_transcript_with_timestamps(
                    video_data.transcript,
                    video_data.chapters,
                )
            else:
                formatted = video_data.transcript.full_text

            # Save to file if requested
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(formatted)
                print(f"\n✅ Transcript saved to: {output_file}")

            # Print first 2000 chars as preview
            print("\n📜 Transcript Preview (first 2000 chars):")
            print("-" * 50)
            print(formatted[:2000])
            if len(formatted) > 2000:
                print(f"\n... (truncated, {len(formatted)} total chars)")
            print("-" * 50)

            return formatted
        print("❌ No transcript available for this video")
        return ""

    finally:
        await deps.cleanup()


async def get_metadata_only(url: str) -> dict:
    """
    Get video metadata without ingesting.

    Args:
        url: YouTube video URL

    Returns:
        Metadata dictionary
    """
    from workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
    from workflows.ingestion.youtube_rag.models import GetYouTubeMetadataRequest
    from workflows.ingestion.youtube_rag.tools import get_youtube_metadata

    logger.info(f"Getting metadata for: {url}")

    deps = YouTubeRAGDeps.from_settings(skip_mongodb=True)
    await deps.initialize()

    try:
        request = GetYouTubeMetadataRequest(
            url=url,
            include_transcript=False,
        )

        result = await get_youtube_metadata(deps, request)

        print("\n" + "=" * 70)
        print("📊 YouTube Video Metadata")
        print("=" * 70)

        if result.metadata:
            meta = result.metadata
            print(f"📝 Title: {meta.title}")
            print(f"📺 Channel: {meta.channel_name}")
            print(f"🆔 Video ID: {meta.video_id}")
            print(f"⏱️  Duration: {meta.duration_seconds // 60} minutes")
            print(f"👀 Views: {meta.view_count:,}" if meta.view_count else "👀 Views: N/A")
            print(f"👍 Likes: {meta.like_count:,}" if meta.like_count else "👍 Likes: N/A")
            print(f"📅 Upload Date: {meta.upload_date}")
            print(f"🏷️  Tags: {', '.join(meta.tags[:10])}" if meta.tags else "🏷️  Tags: None")

        if result.chapters:
            print(f"\n📑 Chapters ({len(result.chapters)}):")
            for ch in result.chapters[:10]:
                minutes = int(ch.start_time // 60)
                seconds = int(ch.start_time % 60)
                print(f"  [{minutes:02d}:{seconds:02d}] {ch.title}")

        if result.errors:
            print(f"\n⚠️  Errors: {result.errors}")

        print("=" * 70)

        return result.model_dump()

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest YouTube video into RAG with Graphiti temporal episodes"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_VIDEO_URL,
        help="YouTube video URL",
    )
    parser.add_argument(
        "--extract-entities",
        action="store_true",
        help="Extract entities using LLM (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--extract-topics",
        action="store_true",
        help="Classify topics using LLM (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--extract-key-moments",
        action="store_true",
        help="Extract key moments using LLM (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only get metadata, don't ingest",
    )
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Only extract transcript, don't ingest",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for transcript (only with --transcript-only)",
    )

    args = parser.parse_args()

    if args.metadata_only:
        asyncio.run(get_metadata_only(args.url))
    elif args.transcript_only:
        asyncio.run(get_transcript_only(args.url, args.output))
    else:
        asyncio.run(
            ingest_youtube_video(
                url=args.url,
                extract_entities=args.extract_entities,
                extract_topics=args.extract_topics,
                extract_key_moments=args.extract_key_moments,
            )
        )
