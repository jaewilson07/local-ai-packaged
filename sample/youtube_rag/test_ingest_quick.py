#!/usr/bin/env python3
"""Quick test script to verify YouTube RAG ingestion works."""

import asyncio
import logging
import sys
from pathlib import Path

# Setup path for direct execution
project_root = Path(__file__).parent.parent.parent
lambda_src = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Test ingestion."""
    from workflows.ingestion.youtube_rag.dependencies import YouTubeRAGDeps
    from workflows.ingestion.youtube_rag.models import IngestYouTubeRequest
    from workflows.ingestion.youtube_rag.tools import ingest_youtube_video

    print("=" * 60)
    print(" YouTube RAG Ingestion Test")
    print("=" * 60)

    deps = YouTubeRAGDeps.from_settings(skip_mongodb=True)
    await deps.initialize()

    try:
        request = IngestYouTubeRequest(
            url="https://www.youtube.com/watch?v=A3DKwLORVe4",
            extract_chapters=True,
            extract_entities=False,
            extract_topics=False,
            chunk_by_chapters=True,
        )

        print(f"Ingesting: {request.url}")
        result = await ingest_youtube_video(
            deps, request, user_id="test-user", user_email="test@example.com"
        )

        print("\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Title: {result.title}")
        print(f"  Document ID: {result.document_id}")
        print(f"  Chunks Created: {result.chunks_created}")

        if result.errors:
            print(f"  Errors: {result.errors}")

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
