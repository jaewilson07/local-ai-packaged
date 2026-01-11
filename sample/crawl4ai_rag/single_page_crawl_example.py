#!/usr/bin/env python3
"""Single page crawl example using Crawl4AI RAG.

This example demonstrates how to crawl a single web page and automatically
ingest it into MongoDB RAG for immediate searchability.

The crawled content is:
- Extracted as markdown
- Chunked into smaller pieces
- Embedded using embeddings model
- Stored in MongoDB with vector indexes

Prerequisites:
- MongoDB running
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_single_page
from server.projects.shared.context_helpers import create_run_context

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Crawl a single page and ingest into MongoDB RAG."""
    # Example URLs to crawl
    urls = [
        "https://www.bluesmuse.dance/",  # Blues Muse Dance website
    ]

    chunk_size = 1000
    chunk_overlap = 200

    print("=" * 80)
    print("Crawl4AI RAG - Single Page Crawl Example")
    print("=" * 80)
    print()
    print("This example demonstrates crawling a single web page and")
    print("automatically ingesting it into MongoDB RAG.")
    print()
    print("The crawled content is:")
    print("  - Extracted as markdown")
    print("  - Chunked into smaller pieces")
    print("  - Embedded using embeddings model")
    print("  - Stored in MongoDB with vector indexes")
    print()
    print("Configuration:")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Chunk overlap: {chunk_overlap}")
    print()

    # Initialize dependencies
    deps = Crawl4AIDependencies()
    await deps.initialize()

    try:
        # Create run context using helper
        ctx = create_run_context(deps)

        # Crawl and ingest each URL
        for i, url in enumerate(urls, 1):
            print(f"\n{'=' * 80}")
            print(f"URL {i}: {url}")
            print("=" * 80)

            logger.info(f"🚀 Starting crawl and ingestion for: {url}")

            # Crawl and ingest
            result = await crawl_and_ingest_single_page(
                ctx=ctx, url=url, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )

            # Display results
            print("\n✅ Crawl and ingestion completed!")
            print(f"   Success: {result['success']}")
            print(f"   Pages crawled: {result['pages_crawled']}")
            print(f"   Chunks created: {result['chunks_created']}")
            if result.get("document_id"):
                print(f"   Document ID: {result['document_id']}")

            if result.get("errors"):
                print(f"   ⚠️  Errors ({len(result['errors'])}):")
                for error in result["errors"][:3]:
                    print(f"      - {error}")

        print("\n" + "=" * 80)
        print("✅ Single page crawl examples completed!")
        print("=" * 80)
        print()
        print("The crawled pages are now searchable via MongoDB RAG.")
        print("Run semantic_search_example.py or hybrid_search_example.py to test.")
        print("=" * 80)

    except Exception as e:
        logger.exception(f"❌ Error during crawl: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
