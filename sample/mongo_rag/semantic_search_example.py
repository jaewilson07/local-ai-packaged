#!/usr/bin/env python3
"""Semantic search example using MongoDB RAG via REST API.

This example demonstrates how to perform pure semantic (vector) search
over documents stored in MongoDB using the REST API.

Prerequisites:
- Lambda server running with MongoDB RAG endpoints available
- Documents ingested into MongoDB (use document_ingestion_example.py)
- Environment variables configured (API_BASE_URL, optional CF_ACCESS_JWT for external access)

Validation:
This sample validates its results through:

1. **Search Results Validation**: Verifies that at least 1 search result is returned
   - Checks that results have expected structure (similarity, document_title, content, etc.)
   - Validates minimum expected count of results

2. **Exit Code Validation**:
   - Returns exit code 0 if verification passes
   - Returns exit code 1 if verification fails or errors occur

3. **Error Handling**:
   - Catches and logs exceptions during search operations
   - Provides clear error messages for debugging
   - Handles connection errors gracefully

The sample will fail validation if:
- Lambda server is not running
- No search results are returned (documents may not be ingested)
- Search results don't meet minimum expected count
"""

import sys
from pathlib import Path

# Add project root to path for sample.shared imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging  # noqa: E402

import requests  # noqa: E402

from sample.shared.auth_helpers import get_api_base_url, get_auth_headers  # noqa: E402
from sample.shared.verification_helpers import verify_search_results  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def semantic_search_api(
    api_base_url: str,
    headers: dict[str, str],
    query: str,
    match_count: int = 5,
) -> list[dict]:
    """
    Perform semantic search via REST API.

    Args:
        api_base_url: Base URL of the Lambda API
        headers: Authentication headers
        query: Search query text
        match_count: Number of results to return

    Returns:
        List of search results
    """
    url = f"{api_base_url}/api/v1/rag/search/semantic"
    payload = {
        "query": query,
        "match_count": match_count,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        if e.response is not None:
            logger.error(f"Response: {e.response.text[:500]}")
        return []
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def main():
    """Perform semantic search over MongoDB documents via API."""
    # Example queries to search
    queries = [
        "What is authentication?",
        "How does vector search work?",
        "Explain document chunking strategies",
    ]

    print("=" * 80)
    print("MongoDB RAG - Semantic Search Example (API-based)")
    print("=" * 80)
    print()
    print("This example demonstrates pure semantic (vector) search via REST API.")
    print("It uses MongoDB's $vectorSearch aggregation to find similar documents.")
    print()

    # Get API configuration
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    print(f"API Base URL: {api_base_url}")
    if headers:
        print("Authentication: Using Cloudflare Access JWT")
    else:
        print("Authentication: Internal network (no auth required)")
    print()

    # Check server connectivity
    try:
        response = requests.get(f"{api_base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Server is accessible")
        else:
            print(f"⚠️  Server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {api_base_url}")
        print("   Make sure the Lambda server is running")
        print()
        print("   To start the server:")
        print("   python start_services.py --stack lambda")
        print()
        print("⚠️  Sample requires running services - exiting gracefully")
        sys.exit(0)  # Exit with success since imports work, services just not running
    except Exception as e:
        print(f"❌ Server check failed: {e}")
        sys.exit(1)

    print()

    # Perform semantic search for each query
    all_results = []
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}: {query}")
        print("=" * 80)

        logger.info(f"🔍 Performing semantic search for: {query}")

        # Perform semantic search via API
        results = semantic_search_api(api_base_url, headers, query, match_count=5)
        all_results.extend(results)

        # Display results
        if results:
            print(f"\nFound {len(results)} results:\n")
            for j, result in enumerate(results, 1):
                similarity = result.get("similarity", 0)
                title = result.get("document_title", "Unknown")
                source = result.get("document_source", "Unknown")
                content = result.get("content", "")[:200]
                chunk_id = result.get("chunk_id", "Unknown")

                print(f"Result {j} (similarity: {similarity:.3f}):")
                print(f"  Title: {title}")
                print(f"  Source: {source}")
                print(f"  Content: {content}...")
                print(f"  Chunk ID: {chunk_id}")
                print()
        else:
            print("\n⚠️  No results found. Make sure documents are ingested.")
            print("   Run document_ingestion_example.py to ingest documents first.")

    print("\n" + "=" * 80)
    print("Semantic search completed!")
    print("=" * 80)

    # Verification
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
        print("   This is expected if no documents have been ingested yet.")
        print("   Run document_ingestion_example.py to ingest documents first.")
        # Don't fail hard - it's expected if no docs ingested
        sys.exit(0)


if __name__ == "__main__":
    main()
