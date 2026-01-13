#!/usr/bin/env python3
"""Adaptive crawl example using Crawl4AI RAG.

This example demonstrates adaptive crawling strategies by:
- Starting with a shallow crawl to assess site structure
- Adjusting depth based on site size
- Using domain filtering to focus on relevant content
- Dynamically adjusting chunk sizes based on content type

This is a more advanced example showing how to adapt crawling
parameters based on the website being crawled.

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

import logging  # noqa: E402

from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies  # noqa: E402
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_deep  # noqa: E402
from server.projects.shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate adaptive crawling strategies."""
    # Example websites with different characteristics
    sites = [
        {
            "url": "https://www.mongodb.com/docs/",
            "name": "MongoDB Documentation",
            "expected_size": "large",
            "suggested_depth": 3,
            "suggested_domains": ["mongodb.com"],
            "suggested_subdomains": ["docs", "www"],
        },
        {
            "url": "https://example.com",
            "name": "Small Website",
            "expected_size": "small",
            "suggested_depth": 2,
            "suggested_domains": None,
            "suggested_subdomains": None,
        },
    ]

    print("=" * 80)
    print("Crawl4AI RAG - Adaptive Crawl Example")
    print("=" * 80)
    print()
    print("This example demonstrates adaptive crawling strategies:")
    print("  - Adjusting depth based on site size")
    print("  - Using domain filtering for focused crawls")
    print("  - Optimizing chunk sizes for different content types")
    print()

    # Initialize dependencies
    deps = Crawl4AIDependencies()
    await deps.initialize()

    try:
        # Create run context using helper
        ctx = create_run_context(deps)

        # Process each site with adaptive strategies
        for site in sites:
            print(f"\n{'=' * 80}")
            print(f"Site: {site['name']}")
            print(f"URL: {site['url']}")
            print("=" * 80)
            print()

            # Strategy 1: Start with shallow crawl to assess structure
            print("📊 Strategy 1: Shallow crawl to assess structure")
            print("   Depth: 1 (shallow)")
            print()

            shallow_result = await crawl_and_ingest_deep(
                ctx=ctx,
                start_url=site["url"],
                max_depth=1,  # Shallow crawl first
                allowed_domains=site["suggested_domains"],
                allowed_subdomains=site["suggested_subdomains"],
                chunk_size=1000,
                chunk_overlap=200,
                max_concurrent=5,
            )

            print(f"   Pages found: {shallow_result['pages_crawled']}")
            print(f"   Chunks created: {shallow_result['chunks_created']}")
            print()

            # Strategy 2: Adjust depth based on initial results
            if shallow_result["pages_crawled"] > 10:
                print("📈 Strategy 2: Site is large, using deeper crawl")
                print(f"   Depth: {site['suggested_depth']} (adjusted)")
                print()

                deep_result = await crawl_and_ingest_deep(
                    ctx=ctx,
                    start_url=site["url"],
                    max_depth=site["suggested_depth"],
                    allowed_domains=site["suggested_domains"],
                    allowed_subdomains=site["suggested_subdomains"],
                    chunk_size=1000,
                    chunk_overlap=200,
                    max_concurrent=10,
                )

                print(f"   Total pages crawled: {deep_result['pages_crawled']}")
                print(f"   Total chunks created: {deep_result['chunks_created']}")
            else:
                print("📉 Strategy 2: Site is small, shallow crawl sufficient")
                print("   Using results from shallow crawl")

            print()

        print("=" * 80)
        print("✅ Adaptive crawl examples completed!")
        print("=" * 80)
        print()
        print("Key adaptive strategies demonstrated:")
        print("  - Start shallow to assess site structure")
        print("  - Adjust depth based on initial results")
        print("  - Use domain filtering for focused crawls")
        print("  - Optimize concurrent sessions based on site size")
        print("=" * 80)

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_rag_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        # Get total chunks from results
        total_chunks = 0
        if shallow_result.get("success"):
            total_chunks += shallow_result.get("chunks_created", 0)
        if deep_result and deep_result.get("success"):
            total_chunks += deep_result.get("chunks_created", 0)

        success, message = verify_rag_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_documents_min=1,
            expected_chunks_min=total_chunks if total_chunks > 0 else None,
        )
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed (data may need time to propagate)")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
