#!/usr/bin/env python3
"""Crawl Blues Muse website and validate MongoDB RAG ingestion.

This script performs:
1. Shallow 1-page scrape of https://www.bluesmuse.dance/
2. Deep scrape of the site (depth 2)
3. Validates content is ingested into MongoDB RAG
"""

import asyncio
import sys
from datetime import datetime
from typing import Any

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
BLUES_MUSE_URL = "https://www.bluesmuse.dance/"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_DEPTH = 2  # Shallow deep crawl to avoid timeout


async def check_server_health() -> bool:
    """Check if the Lambda server is healthy."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Server is healthy")
                return True
            else:
                print(f"⚠️  Server returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False


async def crawl_single_page(url: str) -> dict[str, Any]:
    """Crawl a single page and ingest into MongoDB RAG."""
    print(f"\n{'=' * 80}")
    print("SHALLOW CRAWL: Single Page")
    print(f"{'=' * 80}")
    print(f"URL: {url}")
    print(f"Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print()

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {"url": url, "chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}

            print("📡 Sending request to /api/v1/crawl/single...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/crawl/single",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                print("✅ Single page crawl successful!")
                print("\nResults:")
                print(f"  - Success: {result.get('success', False)}")
                print(f"  - Pages crawled: {result.get('pages_crawled', 0)}")
                print(f"  - Chunks created: {result.get('chunks_created', 0)}")
                print(f"  - Document ID: {result.get('document_id', 'N/A')}")

                if result.get("errors"):
                    print(f"  - Errors: {len(result['errors'])}")
                    for error in result["errors"][:3]:
                        print(f"    • {error}")

                return result
            else:
                error_text = response.text
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response: {error_text[:500]}")
                return {"success": False, "error": error_text}

    except httpx.TimeoutException:
        print("❌ Request timed out (180 seconds)")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ Error during single page crawl: {e}")
        return {"success": False, "error": str(e)}


async def crawl_deep(url: str, max_depth: int) -> dict[str, Any]:
    """Perform deep crawl and ingest into MongoDB RAG."""
    print(f"\n{'=' * 80}")
    print("DEEP CRAWL: Recursive")
    print(f"{'=' * 80}")
    print(f"URL: {url}")
    print(f"Max depth: {max_depth}")
    print(f"Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print()

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            payload = {
                "url": url,
                "max_depth": max_depth,
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "allowed_domains": ["bluesmuse.dance", "www.bluesmuse.dance"],
            }

            print("📡 Sending request to /api/v1/crawl/deep...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/crawl/deep",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                print("✅ Deep crawl successful!")
                print("\nResults:")
                print(f"  - Success: {result.get('success', False)}")
                print(f"  - Pages crawled: {result.get('pages_crawled', 0)}")
                print(f"  - Chunks created: {result.get('chunks_created', 0)}")
                print(f"  - Documents created: {len(result.get('document_ids', []))}")

                if result.get("errors"):
                    print(f"  - Errors: {len(result['errors'])}")
                    for error in result["errors"][:5]:
                        print(f"    • {error}")

                return result
            else:
                error_text = response.text
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response: {error_text[:500]}")
                return {"success": False, "error": error_text}

    except httpx.TimeoutException:
        print("❌ Request timed out (300 seconds)")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ Error during deep crawl: {e}")
        return {"success": False, "error": str(e)}


async def validate_mongodb_ingestion(search_query: str = "Blues Muse") -> dict[str, Any]:
    """Validate that crawled content is searchable in MongoDB RAG."""
    print(f"\n{'=' * 80}")
    print("VALIDATION: MongoDB RAG Search")
    print(f"{'=' * 80}")
    print(f"Search query: '{search_query}'")
    print()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"query": search_query, "search_type": "hybrid", "match_count": 10}

            print("📡 Searching MongoDB RAG...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/rag/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                matches = result.get("results", [])
                print(f"✅ Found {len(matches)} matches")

                if matches:
                    print(f"\nTop {min(3, len(matches))} results:")
                    for i, match in enumerate(matches[:3], 1):
                        score = match.get("score", 0)
                        source = match.get("source", "Unknown")
                        text_preview = match.get("text", "")[:150]
                        print(f"\n  {i}. Score: {score:.4f}")
                        print(f"     Source: {source}")
                        print(f"     Preview: {text_preview}...")

                return {"success": True, "matches": len(matches), "results": matches}
            else:
                error_text = response.text
                print(f"❌ Search failed with status {response.status_code}")
                print(f"Response: {error_text[:500]}")
                return {"success": False, "error": error_text}

    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """Main execution."""
    print("=" * 80)
    print("BLUES MUSE CRAWL & RAG VALIDATION")
    print("=" * 80)
    print(f"Target URL: {BLUES_MUSE_URL}")
    print(f"API Base: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Step 1: Check server health
    if not await check_server_health():
        print("\n❌ Server is not healthy. Please ensure the Lambda server is running.")
        sys.exit(1)

    # Step 2: Shallow crawl (single page)
    single_result = await crawl_single_page(BLUES_MUSE_URL)

    if not single_result.get("success"):
        print("\n⚠️  Single page crawl failed, but continuing with deep crawl...")

    # Wait a bit between crawls
    await asyncio.sleep(2)

    # Step 3: Deep crawl
    deep_result = await crawl_deep(BLUES_MUSE_URL, MAX_DEPTH)

    if not deep_result.get("success"):
        print("\n⚠️  Deep crawl failed")

    # Wait a bit for ingestion to complete
    await asyncio.sleep(3)

    # Step 4: Validate MongoDB RAG ingestion
    validation_result = await validate_mongodb_ingestion("Blues Muse")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Single page crawl: {'✅ Success' if single_result.get('success') else '❌ Failed'}")
    if single_result.get("success"):
        print(f"  - Chunks: {single_result.get('chunks_created', 0)}")

    print(f"Deep crawl: {'✅ Success' if deep_result.get('success') else '❌ Failed'}")
    if deep_result.get("success"):
        print(f"  - Pages: {deep_result.get('pages_crawled', 0)}")
        print(f"  - Chunks: {deep_result.get('chunks_created', 0)}")

    print(
        f"MongoDB RAG validation: {'✅ Success' if validation_result.get('success') else '❌ Failed'}"
    )
    if validation_result.get("success"):
        print(f"  - Matches found: {validation_result.get('matches', 0)}")

    print(f"\n{'=' * 80}")

    # Exit code
    if (
        single_result.get("success")
        and deep_result.get("success")
        and validation_result.get("success")
    ):
        print("✅ All operations completed successfully!")
        sys.exit(0)
    else:
        print("⚠️  Some operations failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
