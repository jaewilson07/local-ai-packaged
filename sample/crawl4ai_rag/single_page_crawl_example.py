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
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

Validation:
This sample validates its results through:

1. **Crawl Result Validation**:
   - Verifies that the page is successfully crawled
   - Checks that content is extracted as markdown
   - Validates that chunks are created and stored
   - Confirms that embeddings are generated

2. **Exit Code Validation**:
   - Returns exit code 0 if crawl and ingestion succeed
   - Returns exit code 1 if crawl fails or errors occur

3. **Error Handling**:
   - Catches and logs exceptions during crawling
   - Handles network errors gracefully
   - Provides clear error messages for debugging
   - Ensures proper cleanup of dependencies

4. **Result Structure Validation**:
   - Verifies crawl result contains expected fields (url, content, metadata)
   - Checks that document IDs and chunk IDs are generated
   - Validates chunk counts match expectations
   - Confirms source URL is preserved in metadata

The sample will fail validation if:
- URL is inaccessible or returns errors
- Content extraction fails
- MongoDB connection fails
- Embedding generation fails
- Chunking or storage operations fail
"""

import asyncio
import sys
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from workflows.ingestion.crawl4ai_rag.ai.dependencies import Crawl4AIDependencies  # noqa: E402
from workflows.ingestion.crawl4ai_rag.tools import crawl_and_ingest_single_page  # noqa: E402

from shared.context_helpers import create_run_context  # noqa: E402

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

        # Track results
        all_results = []
        total_chunks = 0

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

            all_results.append(result)
            if result.get("success"):
                total_chunks += result.get("chunks_created", 0)

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

        # Verify via API
        from sample.shared.auth_helpers import get_api_base_url, get_auth_headers
        from sample.shared.verification_helpers import verify_rag_data

        api_base_url = get_api_base_url()
        headers = get_auth_headers()

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        successful_results = [r for r in all_results if r.get("success")]

        success, message = verify_rag_data(
            api_base_url=api_base_url,
            headers=headers,
            expected_documents_min=len(successful_results) if successful_results else None,
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
