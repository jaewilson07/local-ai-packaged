"""
Direct test of search_web function without going through the server.

This tests the implementation directly to validate it works.
"""

import asyncio
import os
import sys

# Set minimal environment variables before imports
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_db")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")
os.environ.setdefault("SEARXNG_URL", "http://searxng:8080")

# Add the lambda directory to the path
lambda_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../04-lambda"))
sys.path.insert(0, lambda_dir)

from server.projects.deep_research.dependencies import DeepResearchDeps
from server.projects.deep_research.models import SearchWebRequest
from server.projects.deep_research.tools import search_web


async def test_search():
    """Test search_web function directly."""
    print("=" * 80)
    print("Direct Test: search_web for 'blues muse'")
    print("=" * 80)
    print()

    # Initialize dependencies
    print("Initializing dependencies...")
    deps = DeepResearchDeps.from_settings()
    await deps.initialize()

    try:
        # Create request
        request = SearchWebRequest(query="blues muse", result_count=5)

        # Call search_web
        print(f"Searching for: '{request.query}'...")
        result = await search_web(deps, request)

        # Display results
        print()
        print("✓ Search completed!")
        print(f"  Success: {result.success}")
        print(f"  Count: {result.count}")
        print(f"  Query: {result.query}")
        print()

        if result.results:
            print("Results:")
            for i, res in enumerate(result.results[:3], 1):
                print(f"  {i}. {res.title}")
                print(f"     URL: {res.url}")
                print(f"     Snippet: {res.snippet[:100]}...")
                print()
        else:
            print("  No results returned")

        return result.success and result.count > 0

    finally:
        await deps.cleanup()


if __name__ == "__main__":
    success = asyncio.run(test_search())
    sys.exit(0 if success else 1)
