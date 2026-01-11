#!/usr/bin/env python3
"""Deep crawl https://www.bluesmuse.dance/ using crawl4ai-rag.

This script performs a deep crawl of the Blues Muse Dance website and
automatically ingests all discovered pages into MongoDB and Graphiti (if enabled).
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging

from pydantic_ai import RunContext

from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_deep

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Perform deep crawl of Blues Muse Dance website."""
    url = "https://www.bluesmuse.dance/"
    max_depth = 3  # Crawl up to 3 levels deep
    chunk_size = 1000
    chunk_overlap = 200

    print("=" * 80)
    print("Deep Crawl - Blues Muse Dance Website")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Max Depth: {max_depth}")
    print(f"Chunk Size: {chunk_size}")
    print(f"Chunk Overlap: {chunk_overlap}")
    print()

    # Initialize dependencies
    deps = Crawl4AIDependencies()
    await deps.initialize()

    try:
        # Create run context
        ctx = RunContext(deps=deps)

        # Perform deep crawl and ingestion
        logger.info(f"🚀 Starting deep crawl of {url}")
        result = await crawl_and_ingest_deep(
            ctx=ctx,
            start_url=url,
            max_depth=max_depth,
            allowed_domains=None,  # Allow all domains from starting URL
            allowed_subdomains=None,  # Allow all subdomains
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_concurrent=10,
        )

        # Display results
        print("\n" + "=" * 80)
        print("CRAWL RESULTS")
        print("=" * 80)
        print(f"Success: {result['success']}")
        print(f"Starting URL: {result['url']}")
        print(f"Pages Crawled: {result['pages_crawled']}")
        print(f"Chunks Created: {result['chunks_created']}")
        print(f"Documents Created: {len(result['document_ids'])}")

        if result["document_ids"]:
            print("\nFirst 10 Document IDs:")
            for doc_id in result["document_ids"][:10]:
                print(f"  - {doc_id}")
            if len(result["document_ids"]) > 10:
                print(f"  ... and {len(result['document_ids']) - 10} more")

        if result["errors"]:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result["errors"][:10]:
                print(f"  - {error}")
            if len(result["errors"]) > 10:
                print(f"  ... and {len(result['errors']) - 10} more errors")
        else:
            print("\n✅ No errors!")

        print("\n" + "=" * 80)
        print("NOTE: If Graphiti is enabled (USE_GRAPHITI=true),")
        print("      all crawled content has also been ingested into Graphiti!")
        print("=" * 80)

        if result["success"]:
            print("\n✅ Deep crawl completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Deep crawl completed with errors")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Error during deep crawl: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
