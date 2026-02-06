#!/usr/bin/env python3
"""Direct script to crawl a website using crawl4ai-rag.

This script uses the unified ingestion architecture via ContentIngestionService.
Designed to run inside the Docker container.
"""

import asyncio
import sys

# Add /app to path so imports work
sys.path.insert(0, "/app")

from pydantic_ai import RunContext
from app.workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies
from app.workflows.ingestion.crawl4ai_rag.tools import crawl_and_ingest_deep


async def main():
    """Crawl a website and ingest into MongoDB using centralized ingestion."""
    if len(sys.argv) < 2:
        print("Usage: python crawl_website.py <url> [max_depth] [allowed_domains]")
        print("Example: python crawl_website.py https://www.bluesmuse.dance/ 3")
        sys.exit(1)

    url = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    allowed_domains = sys.argv[3].split(",") if len(sys.argv) > 3 else None

    print(f"Starting deep crawl of {url} with max_depth={max_depth}")
    if allowed_domains:
        print(f"Allowed domains: {allowed_domains}")

    # Create dependencies - no MongoDB needed since we use ContentIngestionService
    deps = Crawl4AIDependencies.from_settings(skip_mongodb=True, skip_openai=True)
    await deps.initialize()

    try:
        # Use the unified crawl_and_ingest_deep function
        ctx = RunContext(deps=deps)
        result = await crawl_and_ingest_deep(
            ctx=ctx,
            start_url=url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=None,
            chunk_size=1000,
            chunk_overlap=200,
            max_concurrent=10,
        )

        if not result["success"]:
            print(f"❌ Crawl failed: {result.get('errors', [])}")
            return

        print("\n✅ Crawl complete!")
        print(f"   Pages crawled: {result['pages_crawled']}")
        print(f"   Chunks created: {result['chunks_created']}")
        print(f"   Documents created: {len(result.get('document_ids', []))}")
        if result.get("errors"):
            print(f"   Errors: {len(result['errors'])}")
            for error in result["errors"][:5]:  # Show first 5 errors
                print(f"     - {error}")

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
