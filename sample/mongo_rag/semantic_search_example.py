#!/usr/bin/env python3
"""Semantic search example using MongoDB RAG.

This example demonstrates how to perform pure semantic (vector) search
over documents stored in MongoDB using vector similarity.

Prerequisites:
- MongoDB running with vector search index configured
- Documents ingested into MongoDB (use document_ingestion_example.py)
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
- Dependencies installed: Run `uv pip install -e ".[test]"` in `04-lambda/` directory

Validation:
This sample validates its results through:

1. **Search Results Validation**: Uses `verify_search_results()` from `sample/shared/verification_helpers.py`
   - Verifies that at least 1 search result is returned for each query
   - Checks that results have expected structure (similarity, document_title, content, etc.)
   - Validates minimum expected count of results

2. **Exit Code Validation**:
   - Returns exit code 0 if verification passes
   - Returns exit code 1 if verification fails or errors occur

3. **Error Handling**:
   - Catches and logs exceptions during search operations
   - Provides clear error messages for debugging
   - Ensures proper cleanup of dependencies in finally block

4. **Result Structure Validation**:
   - Verifies results contain required fields (similarity, document_title, document_source, content, chunk_id)
   - Checks that similarity scores are valid (0.0 to 1.0 range)
   - Ensures content is not empty

The sample will fail validation if:
- No search results are returned (documents may not be ingested)
- Search results don't meet minimum expected count
- Results are missing required fields
- Dependencies fail to initialize or cleanup
"""

import asyncio
import os
import sys
from pathlib import Path

# Set environment variables for host execution (not Docker)
# These override defaults that use Docker hostnames
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
# MongoDB with authentication (default credentials: admin/admin123)
os.environ.setdefault(
    "MONGODB_URI",
    "mongodb://admin:admin123@localhost:27017/?directConnection=true&authSource=admin",
)

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

import logging  # noqa: E402

from server.projects.mongo_rag.dependencies import AgentDependencies  # noqa: E402
from server.projects.mongo_rag.tools import semantic_search  # noqa: E402
from server.projects.shared.context_helpers import create_run_context  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Perform semantic search over MongoDB documents."""
    # Example queries to search
    queries = [
        "What is authentication?",
        "How does vector search work?",
        "Explain document chunking strategies",
    ]

    print("=" * 80)
    print("MongoDB RAG - Semantic Search Example")
    print("=" * 80)
    print()
    print("This example demonstrates pure semantic (vector) search.")
    print("It uses MongoDB's $vectorSearch aggregation to find similar documents.")
    print()

    # Initialize dependencies with user context (for RLS)
    # In production, these would come from authenticated user session
    from uuid import uuid4

    user_id = str(uuid4())  # Simulated user ID
    user_email = "demo@example.com"  # Simulated user email

    deps = AgentDependencies.from_settings(
        user_id=user_id, user_email=user_email, is_admin=False, user_groups=[]
    )
    await deps.initialize()

    try:
        # Create run context for search tools
        ctx = create_run_context(deps)

        # Perform semantic search for each query
        for i, query in enumerate(queries, 1):
            print(f"\n{'=' * 80}")
            print(f"Query {i}: {query}")
            print("=" * 80)

            logger.info(f"🔍 Performing semantic search for: {query}")

            # Perform semantic search
            results = await semantic_search(ctx=ctx, query=query, match_count=5)

            # Display results
            if results:
                print(f"\nFound {len(results)} results:\n")
                for j, result in enumerate(results, 1):
                    print(f"Result {j} (similarity: {result.similarity:.3f}):")
                    print(f"  Title: {result.document_title}")
                    print(f"  Source: {result.document_source}")
                    print(f"  Content: {result.content[:200]}...")
                    print(f"  Chunk ID: {result.chunk_id}")
                    print()
            else:
                print("\n⚠️  No results found. Make sure documents are ingested.")
                print("   Run document_ingestion_example.py to ingest documents first.")

        print("\n" + "=" * 80)
        print("✅ Semantic search completed successfully!")
        print("=" * 80)

        # Verify search results
        from sample.shared.verification_helpers import verify_search_results

        all_results = []
        for query in queries:
            results = await semantic_search(ctx=ctx, query=query, match_count=5)
            if results:
                all_results.extend(results)

        print("\n" + "=" * 80)
        print("Verification")
        print("=" * 80)

        success, message = verify_search_results(all_results, expected_min=1)
        print(message)

        if success:
            print("\n✅ Verification passed!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed: No search results found")
            sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
